from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool

    class Config:
        orm_mode = True

class RequestCreate(BaseModel):
    platform: str
    load_date: date
    origin: str
    unload_date: date
    destination: str
    rate_factory: Optional[float] = None
    rate_auction: Optional[float] = None
    cargo_type: str
    weight_volume: str
    vehicle_type: str
    load_unload_type: str
    logistician: str
    ati_price: Optional[float] = None
    is_published: bool = False

class RequestResponse(RequestCreate):
    id: int
    owner_id: int

    class Config:
        orm_mode = True