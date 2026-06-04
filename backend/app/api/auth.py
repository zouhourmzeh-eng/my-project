from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.limiter import limiter

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)
from app.db.base import get_db
from app.models import User
from app.schemas.schemas import (
    RefreshIn, TokenPair, UserCreate, UserLogin, UserOut,
    ChangePasswordIn, ForgotPasswordIn, ResetPasswordIn,
    RegisterOut, VerifyEmailIn, ResendVerificationIn
)
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterOut, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    
    import random
    from datetime import datetime, timedelta, timezone
    code = "".join([str(random.randint(0, 9)) for _ in range(6)])

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_verified=False,
        verification_code=code,
        verification_code_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    db.add(user)
    await db.flush()
    await log_action(db, user.id, "register_pending_verification", "user", user.id)
    await db.commit()
    await db.refresh(user)

    from app.services.email import send_verification_email
    send_verification_email(user.email, code)
    print(f"--- VERIFICATION CODE FOR {user.email}: {code} ---")

    return RegisterOut(
        message="Veuillez confirmer votre compte. Un code de validation à 6 chiffres a été envoyé à votre e-mail.",
        email=user.email
    )


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")
async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    if not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Email not verified")
    await log_action(db, user.id, "login", "user", user.id)
    await db.commit()
    return TokenPair(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id, user.role.value),
        user=UserOut.model_validate(user),
    )


@router.post("/verify-email", response_model=TokenPair)
async def verify_email(payload: VerifyEmailIn, db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timezone
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if user.is_verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already verified")

    if not user.verification_code or user.verification_code != payload.code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid verification code")

    expires_at = user.verification_code_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verification code expired")

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None

    await log_action(db, user.id, "email_verified", "user", user.id)
    await db.commit()
    await db.refresh(user)

    return TokenPair(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id, user.role.value),
        user=UserOut.model_validate(user),
    )


@router.post("/resend-verification", status_code=204)
async def resend_verification(payload: ResendVerificationIn, db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timedelta, timezone
    import random
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if user.is_verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already verified")

    code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    user.verification_code = code
    user.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    await db.commit()

    from app.services.email import send_verification_email
    send_verification_email(user.email, code)
    print(f"--- NEW VERIFICATION CODE FOR {user.email}: {code} ---")


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise ValueError()
        user_id = int(data["sub"])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User invalid")
    return TokenPair(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id, user.role.value),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users/search", response_model=UserOut | None)
async def search_user_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Search a user by exact email address. Returns the user if found, null otherwise."""
    res = await db.execute(
        select(User).where(User.email == email.strip().lower())
    )
    user = res.scalar_one_or_none()
    return user


@router.get("/users/by-id/{user_id}", response_model=UserOut)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a specific user's public info by ID. Used to display team member names."""
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user



@router.post("/change-password", status_code=204)
async def change_password(
    payload: ChangePasswordIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect current password")
    user.hashed_password = hash_password(payload.new_password)
    await log_action(db, user.id, "change_password", "user", user.id)
    await db.commit()


@router.post("/forgot-password", status_code=204)
@limiter.limit("3/minute")
async def forgot_password(request: Request, payload: ForgotPasswordIn, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import or_
    stmt = select(User).where(or_(
        (User.email == payload.email) if payload.email else False,
        (User.phone == payload.phone) if payload.phone else False
    ))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        return

    import random
    from datetime import datetime, timedelta, timezone
    code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    user.recovery_code = code
    user.recovery_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    await db.commit()

    # Send via configured SMTP or log to console
    from app.services.email import send_recovery_email
    if user.email:
        send_recovery_email(user.email, code)
    
    target = user.email if payload.email else user.phone
    print(f"--- RECOVERY CODE FOR {target}: {code} ---")


@router.post("/reset-password", status_code=204)
@limiter.limit("5/minute")
async def reset_password(request: Request, payload: ResetPasswordIn, db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timezone
    from sqlalchemy import or_
    stmt = select(User).where(or_(
        (User.email == payload.email) if payload.email else False,
        (User.phone == payload.phone) if payload.phone else False
    ))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user or not user.recovery_code or user.recovery_code != payload.code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired recovery code")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    # Ensure both are aware or both are naive. Since model uses timezone=True, we use aware.
    expires_at = user.recovery_code_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at and expires_at < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Recovery code expired")

    user.hashed_password = hash_password(payload.new_password)
    user.recovery_code = None
    user.recovery_code_expires_at = None
    await log_action(db, user.id, "reset_password", "user", user.id)
    await db.commit()
