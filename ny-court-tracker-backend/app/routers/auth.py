import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks

from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token, get_current_user_id
from app.schemas import (
    UserRegister, UserLogin, UserOut, TokenOut,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
)
from app.email.password_reset import send_password_reset_email

RESET_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
async def register(data: UserRegister):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (data.email,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        password_hash = hash_password(data.password)
        cursor = conn.execute(
            """INSERT INTO users (email, password_hash, first_name, last_name, attorney_reg_number)
               VALUES (?, ?, ?, ?, ?)""",
            (data.email, password_hash, data.first_name, data.last_name, data.attorney_reg_number),
        )
        user_id = cursor.lastrowid

        # Create default notification settings
        conn.execute(
            "INSERT INTO notification_settings (user_id) VALUES (?)", (user_id,)
        )

        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    token = create_access_token(user_id)
    return TokenOut(
        access_token=token,
        user=UserOut(
            id=user["id"],
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            attorney_reg_number=user["attorney_reg_number"],
            created_at=user["created_at"],
        ),
    )


@router.post("/login", response_model=TokenOut)
async def login(data: UserLogin):
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (data.email,)
        ).fetchone()

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user["id"])
    return TokenOut(
        access_token=token,
        user=UserOut(
            id=user["id"],
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            attorney_reg_number=user["attorney_reg_number"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserOut)
async def get_me(user_id: int = Depends(get_current_user_id)):
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(
        id=user["id"],
        email=user["email"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        attorney_reg_number=user["attorney_reg_number"],
        created_at=user["created_at"],
    )


def _hash_token(token: str) -> str:
    """Hash a reset token with SHA-256 before storing in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """
    Request a password reset. Always returns a success message regardless of
    whether the email exists (security best practice).
    """
    generic_message = "If an account exists with this email, you will receive a password reset code."

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, email FROM users WHERE email = ?", (data.email,)
        ).fetchone()

        if not user:
            return MessageResponse(message=generic_message)

        # Generate a cryptographically secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
        ).isoformat()

        # Invalidate any previous unused tokens for this user
        conn.execute(
            "UPDATE password_resets SET used_at = CURRENT_TIMESTAMP WHERE user_id = ? AND used_at IS NULL",
            (user["id"],),
        )

        # Store the hashed token
        conn.execute(
            """INSERT INTO password_resets (user_id, token_hash, expires_at)
               VALUES (?, ?, ?)""",
            (user["id"], token_hash, expires_at),
        )

    # Send email in the background so the response is fast
    background_tasks.add_task(send_password_reset_email, user["email"], raw_token)

    return MessageResponse(message=generic_message)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest):
    """
    Reset a user's password using a valid reset token.
    """
    if len(data.new_password) < 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 7 characters",
        )

    token_hash = _hash_token(data.token)
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        reset_row = conn.execute(
            """SELECT pr.id, pr.user_id, pr.expires_at, pr.used_at
               FROM password_resets pr
               WHERE pr.token_hash = ?""",
            (token_hash,),
        ).fetchone()

        if not reset_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        if reset_row["used_at"] is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reset token has already been used",
            )

        if reset_row["expires_at"] < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reset token has expired. Please request a new one.",
            )

        # Update the user's password
        new_hash = hash_password(data.new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, reset_row["user_id"]),
        )

        # Mark token as used
        conn.execute(
            "UPDATE password_resets SET used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (reset_row["id"],),
        )

    return MessageResponse(message="Your password has been reset successfully. You can now sign in with your new password.")
