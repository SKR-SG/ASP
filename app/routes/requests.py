from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Request, User
from app.schemas import RequestCreate, RequestResponse
from app.routes.users import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=RequestResponse)
def create_request(request_data: RequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """ Создание новой заявки (только для авторизованных пользователей) """
    new_request = Request(
        platform=request_data.platform,
        load_date=request_data.load_date,
        origin=request_data.origin,
        unload_date=request_data.unload_date,
        destination=request_data.destination,
        rate_factory=request_data.rate_factory,
        rate_auction=request_data.rate_auction,
        cargo_type=request_data.cargo_type,
        weight_volume=request_data.weight_volume,
        vehicle_type=request_data.vehicle_type,
        load_unload_type=request_data.load_unload_type,
        logistician=request_data.logistician,
        ati_price=request_data.ati_price,
        is_published=request_data.is_published,
        owner_id=current_user.id
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

@router.get("/", response_model=list[RequestResponse])
def get_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """ Получение всех заявок пользователя """
    return db.query(Request).filter(Request.owner_id == current_user.id).all()

@router.get("/{request_id}", response_model=RequestResponse)
def get_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """ Получение конкретной заявки """
    request = db.query(Request).filter(Request.id == request_id, Request.owner_id == current_user.id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return request

@router.put("/{request_id}", response_model=RequestResponse)
def update_request(request_id: int, request_data: RequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """ Обновление заявки """
    request = db.query(Request).filter(Request.id == request_id, Request.owner_id == current_user.id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    request.platform = request_data.platform
    request.load_date = request_data.load_date
    request.origin = request_data.origin
    request.unload_date = request_data.unload_date
    request.destination = request_data.destination
    request.rate_factory = request_data.rate_factory
    request.rate_auction = request_data.rate_auction
    request.cargo_type = request_data.cargo_type
    request.weight_volume = request_data.weight_volume
    request.vehicle_type = request_data.vehicle_type
    request.load_unload_type = request_data.load_unload_type
    request.logistician = request_data.logistician
    request.ati_price = request_data.ati_price
    request.is_published = request_data.is_published

    db.commit()
    db.refresh(request)
    return request

@router.delete("/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """ Удаление заявки """
    request = db.query(Request).filter(Request.id == request_id, Request.owner_id == current_user.id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    db.delete(request)
    db.commit()
    return {"message": "Заявка удалена"}