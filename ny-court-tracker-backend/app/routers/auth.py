from fastapi import APIRouter, HTTPException, status
from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token, get_current_user_id
from app.schemas import UserRegister, UserLogin, UserOut, TokenOut
from fastapi import Depends

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
