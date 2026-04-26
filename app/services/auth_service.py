from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import UserModel
from app.schemas.auth import UserLogin, UserRegister


async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    stmt = select(UserModel).where(UserModel.email == email.lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> UserModel | None:
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, user: UserRegister) -> UserModel:
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    new_user = UserModel(
        email=user.email.lower(),
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def authenticate_user(db: AsyncSession, credentials: UserLogin) -> UserModel:
    user = await get_user_by_email(db, credentials.email)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user
