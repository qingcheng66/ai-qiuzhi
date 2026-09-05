from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    email: str
    name: str


class UserCreate(UserBase):
    pass


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_default: bool = False


class UserLogin(BaseModel):
    email: str | None = None
    user_id: int | None = None