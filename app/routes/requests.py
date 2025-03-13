from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Request, User
from app.schemas import RequestCreate, RequestResponse
from app.routes.users import get_current_user
from app.ati_client import publish_cargo

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=RequestResponse)
async def create_request(request_data: RequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Создание новой заявки (только для авторизованных пользователей)"""
    new_request = Request(
        external_no=request_data.external_no,
        loading_city_id=request_data.loading_city_id,
        unloading_city_id=request_data.unloading_city_id,
        load_date=request_data.load_date,
        unload_date=request_data.unload_date,
        weight=request_data.weight,
        volume=request_data.volume,
        logistician=request_data.logistician,
        ati_price=request_data.ati_price,
        is_published=request_data.is_published,
        is_auction=request_data.is_auction,
        owner_id=current_user.id
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Публикация груза на платформу ATI.SU
    await publish_cargo(new_request)

    return new_request

@router.get("/", response_model=list[RequestResponse])
def get_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Получение всех заявок пользователя"""
    return db.query(Request).filter(Request.owner_id == current_user.id).all()

@router.get("/{request_id}", response_model=RequestResponse)
def get_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Получение конкретной заявки"""
    request = db.query(Request).filter(Request.id == request_id, Request.owner_id == current_user.id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return request

@router.put("/{request_id}", response_model=RequestResponse)
def update_request(request_id: int, request_data: RequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Обновление заявки"""
    request = db.query(Request).filter(Request.id == request_id, Request.owner_id == current_user.id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    request.external_no = request_data.external_no
    request.loading_city_id = request_data.loading_city_id
    request.unloading_city_id = request_data.unloading_city_id
    request.load_date = request_data.load_date
    request.unload_date = request_data.unload_date
    request.weight = request_data.weight
    request.volume = request_data.volume
    request.logistician = request_data.logistician
    request.ati_price = request_data.ati_price
    request.is_published = request_data.is_published
    request.is_auction = request_data.is_auction

    db.commit()
    db.refresh(request)
    return request

@router.delete("/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Удаление заявки"""
    request = db.query(Request).filter(Request.id == request_id, Request.owner_id == current_user.id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    db.delete(request)
    db.commit()
    return {"message": "Заявка удалена"}

@router.post("/requests/{request_id}/publish")
async def publish_request(request_id: int, db: Session = Depends(get_db)):
    """Публикация груза в ATI.SU"""
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    # Подготавливаем данные для публикации
    cargo_data = {
        "loading_city_id": request.loading_city_id,
        "unloading_city_id": request.unloading_city_id,
        "unloading_address": request.unloading_address,
        "cargo_name": request.cargo_type,
        "cargo_weight": request.weight,
        "cargo_volume": request.volume,
        "truck_body_type": request.vehicle_type_id,
        "note": request.note or "Автоматическая публикация",
        "contacts": [request.logistician]  # ID контактов
    }

    try:
        ati_response = await publish_cargo(cargo_data)
        return {"message": "Груз успешно опубликован", "ati_response": ati_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))