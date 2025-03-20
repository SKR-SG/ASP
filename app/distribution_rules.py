from sqlalchemy.orm import Session
from app.models import Logist, DistributionRule

def distribute_order(order, session: Session):
    """Применяет правила распределения и возвращает логиста и расчетную цену."""
    
    # Фильтруем правила по площадке
    rules = session.query(DistributionRule).filter(DistributionRule.platform == order["platform"]).all()
    
    for rule in rules:
        # Проверяем соответствие города загрузки и выгрузки
        if (rule.loading_city in [None, order["loading_city"]]) and \
           (rule.unloading_city in [None, order["unloading_city"]]):

            # Определяем логиста
            logist = session.query(Logist).filter_by(name=rule.logistician).first()
            if not logist:
                continue

            # Рассчитываем ставку для АТИ
            if rule.margin_percent is not None:
                ati_price = order["factory_bid"] * ((100 - rule.margin_percent) / 100)
            else:
                ati_price = None  # Запрос цены

            return {
                "logist_id": logist.id,
                "ati_price": ati_price,
                "auto_publish": rule.auto_publish
            }
    
    return None  # Если не найдено правило
