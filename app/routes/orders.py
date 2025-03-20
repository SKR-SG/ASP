from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from app.database import SessionLocal
from app.models import Order
from app.ati_client import publish_cargo, update_cargo, delete_cargo
from app.transformers.ati_transformer import prepare_order_for_ati

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PriceUpdate(BaseModel):
    new_price: float

@router.post("/{order_id}/publish")
async def publish_order(order_id: int, db: Session = Depends(get_db)):
    """
    Публикация груза в ATI.SU.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    cargo_data = prepare_order_for_ati(order)
    # Оборачиваем синхронную функцию publish_cargo в run_in_threadpool
    ati_response = await run_in_threadpool(publish_cargo, cargo_data)
    if not ati_response:
        raise HTTPException(status_code=500, detail="Ошибка при публикации на ATI.SU")

    return {"message": "Груз успешно опубликован", "ati_response": ati_response}

@router.post("/{order_id}/update")
async def update_order_on_ati(order_id: int, db: Session = Depends(get_db)):
    """
    Обновление данных заявки на ATI.SU.
    Используйте этот эндпоинт для принудительного обновления заявки на ATI.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    cargo_data = prepare_order_for_ati(order)
    # Вызываем синхронную функцию update_cargo через run_in_threadpool
    ati_response = await run_in_threadpool(update_cargo, cargo_data)
    if "error" in ati_response:
        raise HTTPException(status_code=500, detail=ati_response["error"])
    return {"message": "Обновление завершено", "ati_response": ati_response}

@router.post("/{order_id}/delete")
async def delete_order_from_ati(order_id: int, db: Session = Depends(get_db)):
    """
    Удаление груза с ATI.SU.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Запускаем синхронную функцию delete_cargo в пуле потоков, чтобы не блокировать event loop
    ati_response = await run_in_threadpool(delete_cargo, order)
    
    if not ati_response:
        raise HTTPException(status_code=500, detail="Ошибка при удалении с ATI.SU")
    
    return {"message": "Груз успешно удален с ATI.SU"}

@router.patch("/{order_id}/price")
async def update_order_price(order_id: int, price_update: PriceUpdate, db: Session = Depends(get_db)):
    """
    Обновление цены заявки в базе данных.
    Изменение цены на ATI не отправляется автоматически.
    Для принудительного обновления на ATI используйте эндпоинт /{order_id}/update.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    order.ati_price = price_update.new_price
    db.commit()
    
    return {"message": "Цена обновлена в БД. Для обновления на ATI используйте эндпоинт /update."}

@router.get("/")
async def get_orders(db: Session = Depends(get_db)):
    """Возвращает список всех заказов."""
    orders = db.query(Order).all()
    return orders