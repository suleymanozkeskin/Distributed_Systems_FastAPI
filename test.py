# test.py
import asyncio
from main import create_users_concurrently

async def test_create_users_concurrently():
    await create_users_concurrently(1000)

asyncio.run(test_create_users_concurrently())
