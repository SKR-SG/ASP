from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.sync.logists_sync import run_logists_sync
from app.models import Logist

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db    
    finally:
        db.close()

@router.post("/sync")
async def sync_logists_endpoint(background_tasks: BackgroundTasks):
    """
    Эндпоинт для запуска синхронизации логистов.
    Функция run_logists_sync() вызывается в фоне,
    что позволяет не блокировать обработку других запросов.
    """
    try:
        background_tasks.add_task(run_logists_sync)
        return {"message": "Синхронизация логистов запущена"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_logists(db: Session = Depends(get_db)):
    """Возвращает список всех логистов."""
    logists = db.query(Logist).all()
    return logists