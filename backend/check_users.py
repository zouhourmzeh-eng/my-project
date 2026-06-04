import asyncio
import sys
sys.path.append('.')
from app.db.base import AsyncSessionLocal
from app.models import User
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User))
        for u in res.scalars():
            print(f"ID: {u.id}, Email: {u.email}, Role: {u.role}, Phone: {u.phone}")

if __name__ == "__main__":
    asyncio.run(main())
