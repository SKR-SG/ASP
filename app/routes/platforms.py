from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import SessionLocal
from app.models import Platform

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PlatformSchema(BaseModel):
    name: str
    enabled: bool = True
    auth_data: dict | None = None

    class Config:
        orm_mode = True

@router.post("/", response_model=PlatformSchema)
def create_platform(platform_data: PlatformSchema, db: Session = Depends(get_db)):
    new_platform = Platform(
        name=platform_data.name,
        enabled=platform_data.enabled,
        auth_data=platform_data.auth_data,
    )
    db.add(new_platform)
    db.commit()
    db.refresh(new_platform)
    return new_platform

@router.put("/{platform_id}", response_model=PlatformSchema)
def update_platform(platform_id: int, platform_data: PlatformSchema, db: Session = Depends(get_db)):
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Площадка не найдена")
    platform.name = platform_data.name
    platform.enabled = platform_data.enabled
    platform.auth_data = platform_data.auth_data
    db.commit()
    db.refresh(platform)
    return platform

@router.delete("/{platform_id}")
def delete_platform(platform_id: int, db: Session = Depends(get_db)):
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Площадка не найдена")
    db.delete(platform)
    db.commit()
    return {"message": "Площадка удалена"}

@router.get("/")
async def get_platforms(db: Session = Depends(get_db)):
    """Возвращает список всех площадок."""
    platforms = db.query(Platform).all()
    return platforms