import motor.motor_asyncio
from beanie import PydanticObjectId, Document
from fastapi_users.db import BeanieBaseUser, BeanieUserDatabase
from pydantic import Field
from typing import List, Any
from uuid import UUID, uuid4


class User(BeanieBaseUser, Document):
    id: UUID = Field(default_factory=lambda: uuid4())
    thread_id: List[UUID] = Field(default_factory=lambda: [uuid4()]) # List of thread ids as separate chats. For now we will only use 1 thread_id per user
    first_name: str


    class Settings:
        name = "users"
        collection = "users"
        email_collation = {"locale": "en", "strength": 2}


async def get_user_db():
    yield BeanieUserDatabase(User)