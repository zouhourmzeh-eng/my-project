import asyncio
import sys
sys.path.append('.')
from app.db.base import AsyncSessionLocal
from app.models import User
from app.core.security import hash_password
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.email == 'zouhourmzeh@gmail.com'))
        user = res.scalar_one_or_none()
        if user:
            user.hashed_password = hash_password('Password123!')
            await session.commit()
            print("Successfully updated password to Password123!")
        else:
            print("User not found!")

if __name__ == "__main__":
    asyncio.run(main())
