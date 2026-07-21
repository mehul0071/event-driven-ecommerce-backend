from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.v1.routes.auth import get_current_user
from app.schemas.users import UserAccounts, UserRoleUpdate
from app.models.user import UserModel

router = APIRouter()


async def get_current_superuser(current_user=Depends(get_current_user)):
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user


@router.get("/users", response_model=List[UserAccounts])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_superuser=Depends(get_current_superuser)
):
    stmt = select(UserModel)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role_update: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_superuser=Depends(get_current_superuser)
):
    if role_update.role not in ("user", "admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'user', 'admin', or 'super_admin'."
        )
        
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = role_update.role
    user.is_superuser = (role_update.role == "super_admin")
    
    await db.commit()
    await db.refresh(user)
    return {"message": f"User {user.email} role updated to {user.role} successfully"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_superuser=Depends(get_current_superuser)
):
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    if user.id == current_superuser.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
        
    await db.delete(user)
    await db.commit()
    return {"message": f"User {user.email} deleted successfully"}
