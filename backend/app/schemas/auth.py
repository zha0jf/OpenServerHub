from pydantic import BaseModel
from app.schemas.user import UserResponse

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse