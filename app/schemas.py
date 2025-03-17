from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from datetime import datetime

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

class OrderCreate(BaseModel):
    platform: str
    load_date: datetime
    origin: str
    unload_date: datetime
    destination: str
    rate_factory: float
    rate_auction: float
    cargo_type: str
    weight_volume: str
    vehicle_type: str
    load_unload_type: str
    logistician: str
    ati_price: float
    is_published: bool

class OrderResponse(OrderCreate):
    id: int
    owner_id: int

    class Config:
        orm_mode = True