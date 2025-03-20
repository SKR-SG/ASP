import os
import math
import re
from datetime import datetime
from app.models import DistributionRule
from app.ati_client import get_city_id, get_contact_id, get_car_types, get_loading_types, get_unloading_types
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Подключаемся к БД
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Загружаем словари один раз при старте
car_type_dict = get_car_types()
loading_type_dict = get_loading_types()
unloading_type_dict = get_unloading_types()

def prepare_order_for_ati(order):
    """Готовим данные для публикации на АТИ"""

    # 🆕 Поиск ID типа кузова по вхождению ключевого слова
    body_types = [200]  # Дефолтное значение
    for key, type_id in car_type_dict.items():
        if key in order.vehicle_type.lower():
            body_types = [type_id]
            break  # Берем первое найденное совпадение

    print(f"DEBUG: vehicle_type={order.vehicle_type}, body_types={body_types}")

    # 🆕 Обработка loading_types (разделяем на body_loading и body_unloading)
    loading_list = [lt.strip().lower() for lt in order.loading_types.split(",")]

    body_loading = []
    body_unloading = []

    for i, lt in enumerate(loading_list):
        if lt == "полная растентовка":
            # Если "Полная растентовка" стоит первой, записываем оба значения в `body_loading`
            if i == 0:
                if "верхняя" in loading_type_dict:
                    body_loading.append(loading_type_dict["верхняя"])
                if "боковая" in loading_type_dict:
                    body_loading.append(loading_type_dict["боковая"])
            else:
                # Если "Полная растентовка" стоит НЕ первой, записываем в `body_unloading`
                if "верхняя" in unloading_type_dict:
                    body_unloading.append(unloading_type_dict["верхняя"])
                if "боковая" in unloading_type_dict:
                    body_unloading.append(unloading_type_dict["боковая"])
        elif i == 0:  
            # Первый элемент в `body_loading`, если он не "Полная растентовка"
            if lt in loading_type_dict:
                body_loading.append(loading_type_dict[lt])
        else:
            # Остальные элементы в `body_unloading`
            if lt in unloading_type_dict:
                body_unloading.append(unloading_type_dict[lt])

    print(f"DEBUG: loading_types={order.loading_types}, body_loading={body_loading}, body_unloading={body_unloading}")         

    # Рассчитываем вес и объем
    weight = math.ceil(float(order.weight_volume.split(" т")[0]) * 10) / 10
    # Извлекаем `volume`
    match = re.search(r"(\d+)\s*м3", order.vehicle_type)
    if match:
        volume = int(match.group(1))  # Берем только число перед "м3"
    else:
        # Если "м3" нет в строке, берем последнее число
        numbers = re.findall(r"\d+", order.vehicle_type)
        volume = int(numbers[-1]) if numbers else 0

    # Получаем ID городов
    loading_city_id = get_city_id(order.loading_city)
    unloading_city_id = get_city_id(order.unloading_city)

    # Получаем ID логиста
    logist_id = get_contact_id(order.logistician_name)
    
    # Берем `ati_price` из `orders`
    ati_price = order.ati_price

    # Получаем `payment_days` из `distribution_rules`
    rule = session.query(DistributionRule).filter(
        (DistributionRule.loading_city == order.loading_city) | (DistributionRule.loading_city.is_(None)),
        (DistributionRule.unloading_city == order.unloading_city) | (DistributionRule.unloading_city.is_(None))
    ).first()
    payment_days = rule.payment_days if rule and rule.payment_days else 30  # По умолчанию 30 дней

    # 🆕 Проверяем, какой тип у даты, и приводим к `datetime`, если нужно
    load_date_obj = (
        order.load_date if isinstance(order.load_date, datetime) 
        else datetime.strptime(order.load_date, "%Y-%m-%d %H:%M:%S") if order.load_date 
        else None
    )

    unload_date_obj = (
        order.unload_date if isinstance(order.unload_date, datetime) 
        else datetime.strptime(order.unload_date, "%Y-%m-%d %H:%M:%S") if order.unload_date 
        else None
    )

    # 🆕 Формируем `dates` для загрузки
    load_first_date = load_date_obj.strftime("%Y-%m-%d") if load_date_obj else None
    load_time = load_date_obj.strftime("%H:%M") if load_date_obj else None

    load_dates = {
        "type": "from-date",
        "time": {
            "type": "bounded",
            "start": load_time,
            "end": load_time,
            "offset": "+00:00"
        },
        "first_date": load_first_date,
        "last_date": load_first_date
    }

    # 🆕 Формируем `dates` для разгрузки
    unload_first_date = unload_date_obj.strftime("%Y-%m-%d") if unload_date_obj else None
    unload_time = unload_date_obj.strftime("%H:%M") if unload_date_obj else None

    unload_dates = {
        "first_date": unload_first_date,
        "last_date": unload_first_date,
        "time": {
            "type": "round-the-clock" if unload_time is None else "bounded",
            "start": unload_time,
            "end": unload_time,
            "offset": "+00:00"
        }
    }

    # 🆕 Исправленный `payment`
    if ati_price:
        rate_without_nds = math.floor(ati_price / 1.2 / 100) * 100  # Убираем 20% НДС

        payment = {
            "type": "without-bargaining",
            "hide_counter_offers": True,
            "direct_offer": True,
            "payment_mode": {
                "type": "delayed-payment",
                "payment_delay_days": payment_days   
            },
            "currency_type": 1,
            "rate_with_vat": ati_price,  
            "rate_without_vat": rate_without_nds 
        }
    else:
        payment = {
            "type": "rate-request",
            "hide_counter_offers": True,
            "direct_offer": True,
            "payment_mode": {
                "type": "delayed-payment",
                "payment_delay_days": payment_days  
            },
            "currency_type": 1,
            "rate_with_vat_available": True,
            "rate_without_vat_available": True
        }

    # Добавляем `note`
    note = "Аукцион" if order.order_type == "AUCTION" else ""

    return {
        "external_id": order.external_no,
        "cargo_id": order.cargo_id,  # Новая строка – теперь cargo_id берется из заказа
        "loading_city_id": loading_city_id,
        "unloading_city_id": unloading_city_id,
        "loading_address": order.loading_address or"",
        "unloading_address": order.unloading_address or "",
        "cargo_name": order.cargo_name or "Груз",
        "weight": weight,
        "volume": volume,
        "logist_id": logist_id,
        "ati_price": ati_price,
        "note": note,
        "payment": payment,
        "loading_dates": load_dates,  # 🆕 Добавили даты загрузки
        "unloading_dates": unload_dates,  # 🆕 Добавили даты разгрузки
        "body_types": body_types,  # 🆕 Передаем списки, а не структуру
        "body_loading": body_loading,
        "body_unloading": body_unloading
    }