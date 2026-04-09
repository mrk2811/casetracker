import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token, get_current_user_id
from app.schemas import (
    UserRegister, UserLogin, UserOut, TokenOut,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
)
from app.email.password_reset import send_password_reset_email

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


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest):
    """Request a password reset email."""
    with get_db() as conn:
        user = conn.execute(
            "SELECT id, email FROM users WHERE email = ?", (data.email,)
        ).fetchone()

    # Always return success to prevent email enumeration
    if not user:
        return MessageResponse(
            message="If an account with that email exists, a reset code has been sent."
        )

    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    with get_db() as conn:
        # Invalidate any existing unused reset tokens for this user
        conn.execute(
            "DELETE FROM password_resets WHERE user_id = ? AND used_at IS NULL",
            (user["id"],),
        )
        # Store the new token
        conn.execute(
            """INSERT INTO password_resets (user_id, token_hash, expires_at)
               VALUES (?, ?, ?)""",
            (user["id"], token_hash, expires_at.isoformat()),
        )

    # Send the reset email (token, not hash)
    send_password_reset_email(user["email"], token)

    return MessageResponse(
        message="If an account with that email exists, a reset code has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest):
    """Reset password using a valid reset token."""
    if len(data.new_password) < 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 7 characters",
        )

    token_hash = hashlib.sha256(data.token.encode()).hexdigest()

    with get_db() as conn:
        reset_row = conn.execute(
            """SELECT pr.id, pr.user_id, pr.expires_at
               FROM password_resets pr
               WHERE pr.token_hash = ? AND pr.used_at IS NULL""",
            (token_hash,),
        ).fetchone()

        if not reset_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token.",
            )

        # Check expiration
        expires_at = datetime.fromisoformat(reset_row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )

        # Update the user's password
        new_hash = hash_password(data.new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, reset_row["user_id"]),
        )

        # Mark the token as used
        conn.execute(
            "UPDATE password_resets SET used_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), reset_row["id"]),
        )

    return MessageResponse(message="Password has been reset successfully.")


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
