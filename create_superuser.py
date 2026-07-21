import asyncio
import sys
import os
from app.core.database import AsyncSessionLocal
from app.models import UserModel, ProductModel, OrderModel, OrderDetailModel, UserInteractionModel
from app.core.security import get_password_hash
from sqlalchemy import select

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_EMAIL = "superadmin@email.com"
DEFAULT_PASSWORD = "Admin123!"
DEFAULT_NAME = "Super Admin"


async def create_superuser():
    hashed_password = get_password_hash(DEFAULT_PASSWORD)

    async with AsyncSessionLocal() as db:
        stmt = select(UserModel).where(UserModel.email == DEFAULT_EMAIL)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"[CLI Error] User with email '{DEFAULT_EMAIL}' already exists.")
            return

        user = UserModel(
            email=DEFAULT_EMAIL,
            hashed_password=hashed_password,
            full_name=DEFAULT_NAME,
            is_active=True,
            is_superuser=True,
            role="super_admin",
        )

        db.add(user)
        await db.commit()

        print(f"[CLI Success] Superuser '{DEFAULT_EMAIL}' created successfully!")


if __name__ == "__main__":
    asyncio.run(create_superuser())