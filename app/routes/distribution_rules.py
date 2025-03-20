from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import SessionLocal
from app.models import DistributionRule

router = APIRouter()

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic-модель для валидации входящих данных для DistributionRule
class DistributionRuleSchema(BaseModel):
    loading_city: str | None = None           # Город погрузки (может быть None, если универсальное правило)
    unloading_city: str | None = None         # Город выгрузки (может быть None)
    logistician: str                         # Имя логиста
    margin_percent: float | None = None        # Процент маржи для обычных заявок
    auction_margin_percent: float | None = None  # Процент маржи для аукционных заявок
    publish_delay: int | None = 0              # Задержка публикации (в минутах)
    auto_publish: bool = False                # Автоматическая публикация (True/False)
    payment_days: int | None = 30              # Дней оплаты (по умолчанию 30)
    cargo_name: str | None = "Груз"            # Наименование груза

    class Config:
        orm_mode = True  # Это позволяет Pydantic работать с объектами SQLAlchemy

# ──────────────── CREATE (Создание нового правила) ───────────────
@router.post("/", response_model=DistributionRuleSchema)
def create_distribution_rule(rule_data: DistributionRuleSchema, db: Session = Depends(get_db)):
    """
    Создаёт новое правило распределения.
    Пример запроса (JSON):
    {
        "loading_city": "Челябинск",
        "unloading_city": "Москва",
        "logistician": "Кравченко Сергей",
        "margin_percent": 10.0,
        "auction_margin_percent": 15.0,
        "publish_delay": 5,
        "auto_publish": true,
        "payment_days": 30,
        "cargo_name": "Груз"
    }
    """
    new_rule = DistributionRule(
        loading_city=rule_data.loading_city,
        unloading_city=rule_data.unloading_city,
        logistician=rule_data.logistician,
        margin_percent=rule_data.margin_percent,
        auction_margin_percent=rule_data.auction_margin_percent,
        publish_delay=rule_data.publish_delay,
        auto_publish=rule_data.auto_publish,
        payment_days=rule_data.payment_days,
        cargo_name=rule_data.cargo_name,
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule

# ──────────────── UPDATE (Изменение правила) ───────────────
@router.put("/{rule_id}", response_model=DistributionRuleSchema)
def update_distribution_rule(rule_id: int, rule_data: DistributionRuleSchema, db: Session = Depends(get_db)):
    """
    Изменяет правило распределения по его ID.
    В запросе передаётся полное тело правила.
    """
    rule = db.query(DistributionRule).filter(DistributionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    
    # Обновляем поля правила
    rule.loading_city = rule_data.loading_city
    rule.unloading_city = rule_data.unloading_city
    rule.logistician = rule_data.logistician
    rule.margin_percent = rule_data.margin_percent
    rule.auction_margin_percent = rule_data.auction_margin_percent
    rule.publish_delay = rule_data.publish_delay
    rule.auto_publish = rule_data.auto_publish
    rule.payment_days = rule_data.payment_days
    rule.cargo_name = rule_data.cargo_name
    
    db.commit()
    db.refresh(rule)
    return rule

# ──────────────── DELETE (Удаление правила) ───────────────
@router.delete("/{rule_id}")
def delete_distribution_rule(rule_id: int, db: Session = Depends(get_db)):
    """
    Удаляет правило распределения по его ID.
    """
    rule = db.query(DistributionRule).filter(DistributionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    db.delete(rule)
    db.commit()
    return {"message": "Правило удалено"}

@router.get("/")
async def get_distribution_rules(db: Session = Depends(get_db)):
    """Возвращает список всех правил распределения."""
    rules = db.query(DistributionRule).all()
    return rules
