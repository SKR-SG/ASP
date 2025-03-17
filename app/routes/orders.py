from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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

@router.post("/{order_id}/publish")
async def publish_order(order_id: int, db: Session = Depends(get_db)):
    """ Публикация груза в ATI.SU """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    # Преобразуем заявку в формат ATI
    cargo_data = prepare_order_for_ati(order)
    ati_response = await publish_cargo(cargo_data)

    if not ati_response:
        raise HTTPException(status_code=500, detail="Ошибка при публикации на ATI.SU")

    return {"message": "Груз успешно опубликован", "ati_response": ati_response}

@router.post("/{order_id}/update")
async def update_order_on_ati(order_id: int, db: Session = Depends(get_db)):
    """ Обновление данных заявки на ATI.SU """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    # Преобразуем заявку в формат ATI
    cargo_data = prepare_order_for_ati(order)
    ati_response = await update_cargo(cargo_data)

    if not ati_response:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении на ATI.SU")

    return {"message": "Груз успешно обновлен на ATI.SU", "ati_response": ati_response}

@router.post("/{order_id}/delete")
async def delete_order_from_ati(order_id: int, db: Session = Depends(get_db)):
    """ Удаление груза с ATI.SU """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    ati_response = await delete_cargo(order)

    if not ati_response:
        raise HTTPException(status_code=500, detail="Ошибка при удалении с ATI.SU")

    return {"message": "Груз успешно удален с ATI.SU"}
