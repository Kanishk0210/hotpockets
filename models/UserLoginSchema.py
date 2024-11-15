from pydantic import BaseModel, Field, EmailStr

class UserLoginSchema(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)