import os
import requests
import re
from datetime import datetime, timezone
from sqlalchemy import create_engine, or_, Column, Integer, String, Boolean, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import dotenv_values, load_dotenv
from app.models import Order, DistributionRule  # Импорт моделей
from app.ati_client import publish_cargo  # Импорт публикации в АТИ
from app.ati_client import get_city_id  # Импорт функции для получения ID города
from app.distribution_rules import distribute_order  # Импорт функции распределения
from app.transformers.ati_transformer import prepare_order_for_ati  # Импорт функции преобразования

# Загружаем переменные окружения
load_dotenv()
env_values = dotenv_values(".env")  # Загружаем принудительно

# API URL и Токен
T2_API_TOKEN = env_values.get("T2_API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not T2_API_TOKEN:
    print("❌ Ошибка: T2_API_TOKEN не задан!")
    exit()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Authorization": f"Token {T2_API_TOKEN}"
}

# Настройка базы данных
Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# URL-адреса для разных типов заявок
ASSIGNED_ORDERS_URL = "https://api.transport2.ru/carrier/graphql?operation=assignedOrders"
AUCTION_ORDERS_URL = "https://api.transport2.ru/carrier/graphql?operation=auctionNewOrders"
FREE_ORDERS_URL = "https://api.transport2.ru/carrier/graphql?operation=freeOrders"

# Тело запросов
assigned_payload = {
    "query": """
        query {
            assignedOrders {
                id
                externalNo
                loadingPlaces {
                    storagePoint {
                        settlement
                        address
                    }
                }
                unloadingPlaces {
                    storagePoint {
                        settlement
                        address
                    }
                }
                loadingDatetime
                unloadingDatetime
                weight
                volume
                loadingTypes
                comment
                price
                status
                vehicleRequirements {
                    name
                    bodySubtype {
                        name
                    }
                }
            }
        }
    """
}

auction_payload = {
    "query": """
        query {
            auctionOrders {
                id
                externalNo
                loadingPlaces {
                    storagePoint {
                        settlement
                        address
                    }
                }
                unloadingPlaces {
                    storagePoint {
                        settlement
                        address
                    }
                }
                loadingDatetime
                unloadingDatetime
                weight
                volume
                loadingTypes
                comment
                status
                lot {
                    auctionStatus
                    startPrice
                    lastBet
                }
                vehicleRequirements {
                    name
                    bodySubtype {
                        name
                    }
                }
            }
        }
    """
}

free_payload = {
    "query": """
        query {
            freeOrders {
                id
                externalNo
                loadingPlaces {
                    storagePoint {
                        settlement
                        address
                    }
                }
                unloadingPlaces {
                    storagePoint {
                        settlement
                        address
                    }
                }
                loadingDatetime
                unloadingDatetime
                weight
                volume
                loadingTypes
                comment
                price
                status
                vehicleRequirements {
                    name
                    bodySubtype {
                        name
                    }
                }
            }
        }
    """
}

def fetch_orders(url, payload, is_auction=False, is_free=False):
    """Запрашивает только актуальные заявки и фильтрует сразу при загрузке"""
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if response.status_code != 200 or not data.get("data"):
            print(f"⚠️ Ошибка или пустой ответ от API {url}")
            return []

        orders = data["data"].get("assignedOrders", []) if not is_auction and not is_free else \
                 data["data"].get("auctionOrders", []) if is_auction else \
                 data["data"].get("freeOrders", [])

        current_datetime = datetime.now(timezone.utc)  # Текущее время в UTC

        fresh_orders = []
        for order in orders:
            # Проверка даты отгрузки
            loading_datetime_str = order.get("loadingDatetime")
            if not loading_datetime_str:
                continue

            loading_datetime = datetime.fromisoformat(loading_datetime_str)
            if loading_datetime < current_datetime:
                continue  # Пропускаем старые заявки

            # Фильтрация по статусу
            if is_auction:
                if order.get("status") != "FREE" or order.get("lot", {}).get("auctionStatus") != "ACTIVE":
                    continue
            elif is_free:
                if order.get("status") != "FREE":
                    continue
            else:  # Assigned
                if order.get("status") != "ASSIGNED":
                    continue

            fresh_orders.append(order)

        print(f"✅ Загружено {len(fresh_orders)} актуальных заявок ({'Аукцион' if is_auction else 'Свободные' if is_free else 'Назначенные'})")
        return fresh_orders

    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса {url}: {e}")
        return []

def process_orders():
    """Основная функция обработки заявок"""
    assigned_orders = fetch_orders(ASSIGNED_ORDERS_URL, assigned_payload)  # ✅ Уже список
    auction_orders = fetch_orders(AUCTION_ORDERS_URL, auction_payload, is_auction=True)  # ✅ Уже список
    free_orders = fetch_orders(FREE_ORDERS_URL, free_payload, is_free=True)  # ✅ Уже список
    
    all_orders = (
        [(order, "ASSIGNED") for order in assigned_orders] +
        [(order, "AUCTION") for order in auction_orders] +
        [(order, "FREE") for order in free_orders]
    )
   
    for order, order_type in all_orders:
        process_order(order, order_type)
    
def filter_valid_orders(orders, order_type):
    """Фильтруем заявки: проверяем статус и дату отгрузки"""
    current_datetime = datetime.now(timezone.utc)

    valid_orders = []
    for order in orders:
        load_date = order.get("loadingDatetime")
        if not load_date:
            continue

        # Преобразуем дату отгрузки в UTC и проверяем
        load_datetime = datetime.fromisoformat(load_date)
        if load_datetime < current_datetime:
            continue

        # Фильтр для разных типов заявок
        if order_type == "AUCTION":
            if order.get("status") != "FREE" or order.get("lot", {}).get("auctionStatus") != "ACTIVE":
                continue
        elif order_type == "FREE":
            if order.get("status") != "FREE":
                continue
        elif order_type == "ASSIGNED":
            if order.get("status") != "ASSIGNED":
                continue

        valid_orders.append(order)

    return valid_orders

def extract_street_and_house(address):
    """Извлекает улицу и дом из строки адреса"""

    # Удаляем текст в скобках (например, "(Екатеринбург)")
    address = re.sub(r"\(.*?\)", "", address).strip()

    # Разбиваем строку на части
    parts = [part.strip() for part in address.split(",")]

    # Ключевые слова для поиска улицы
    street_keywords = ["ул", "улица", "пр-кт", "проспект", "тракт", "шоссе", "пер", "переулок"]

    street_part = None
    house_number = None

    # Ищем первое поле, похожее на улицу
    for part in parts:
        words = part.split()

        if any(word.lower() in street_keywords for word in words):
            # Нашли улицу! Теперь удаляем "ул", "улица" и сохраняем
            street_part = " ".join([word for word in words if word.lower() not in ["ул", "улица"]]).strip()
            break  # Останавливаемся после нахождения первой улицы

    # Если нашли улицу, проверяем, есть ли номер дома в следующих частях
    if street_part:
        for next_part in parts[parts.index(part) + 1:]:
            if re.search(r"\d", next_part):  # Если есть цифра – это номер дома
                house_number = next_part
                break  # Берем первый найденный номер

    # Формируем итоговый результат
    result = f"{street_part} {house_number}" if house_number else street_part

    print(f"DEBUG: address={address}, result={result}")  # Отладка

    return result


def process_order(order, order_type):
    """Обрабатываем заказ и сохраняем в БД без преобразования для АТИ"""
    external_no = order.get("externalNo", "N/A")

    # Город погрузки и выгрузки
    loading_place = order.get("loadingPlaces", [{}])[0].get("storagePoint", {})
    unloading_place = order.get("unloadingPlaces", [{}])[0].get("storagePoint", {})
    loading_city = loading_place.get("settlement", "N/A")
    unloading_city = unloading_place.get("settlement", "N/A")

    # Адрес формат улица дом
    address = extract_street_and_house(order["unloadingPlaces"][0]["storagePoint"]["address"])

    # Даты
    load_date = order.get("loadingDatetime", "N/A")
    unload_date = order.get("unloadingDatetime", "N/A")

    # Вес и объем
    weight = order.get("weight", 0)
    volume = order.get("volume", 0)
    weight_volume = f"{weight} т / {volume} м³"

    # Тип ТС, тип загрузки/разгрузки
    vehicle_type = order.get("vehicleRequirements", {}).get("name", "N/A")
    loading_types = order.get("loadingTypes", "N/A")

    # Комментарий (может содержать данные о грузе)
    comment = order.get("comment", "N/A")

    # Определяем ставку для аукционных заявок
    if order_type == "AUCTION":
        bid_price = order.get("lot", {}).get("lastBet")
        if bid_price is None:
            bid_price = order.get("lot", {}).get("startPrice")
        bid_price = bid_price if bid_price is not None else 0
    else:
        bid_price = order.get("price", 0)  # Для обычных заявок берем price

    # 🛠 1. Ищем точное совпадение по погрузке и выгрузке
    rule = session.query(DistributionRule).filter(
        DistributionRule.loading_city == loading_city,
        DistributionRule.unloading_city == unloading_city
    ).first()

    # 🛠 2. Если точного совпадения нет, ищем совпадение только по погрузке
    if not rule:
        rule = session.query(DistributionRule).filter(
            DistributionRule.loading_city == loading_city,
            DistributionRule.unloading_city.is_(None)  # Универсальное правило для выгрузки
        ).first()

    # 🛠 3. Если нет совпадений, ищем правило, где загрузка `None` (универсальное)
    if not rule:
        rule = session.query(DistributionRule).filter(
            DistributionRule.loading_city.is_(None),
            DistributionRule.unloading_city == unloading_city
        ).first()

    # 🛠 4. Назначаем логиста
    logistician_name = rule.logistician if rule else None

    if logistician_name:
        print(f"✅ Назначен логист: {logistician_name} для {loading_city} -> {unloading_city}")
    else:
        print(f"❌ Логист не найден для {loading_city} -> {unloading_city}")

    # Получаем наименование груза по правилам распределения
    cargo_name = rule.cargo_name if rule and rule.cargo_name else "Груз без названия"

    # Рассчитываем `ati_price`
    ati_price = None
    if rule and bid_price:  # Проверяем, что rule найден и есть цена
        margin_percent = rule.auction_margin_percent if order_type == "AUCTION" else rule.margin_percent
        if margin_percent is not None:
            ati_price = bid_price * (100 - margin_percent) / 100    

    # Сохраняем в БД
    save_order({
        "external_no": external_no,
        "platform": "Transport2",
        "load_date": load_date,
        "loading_city": loading_city,
        "unloading_city": unloading_city,
        "unload_date": unload_date,
        "weight_volume": weight_volume,
        "vehicle_type": vehicle_type,
        "loading_types": loading_types,
        "comment": comment,
        "cargo_name": cargo_name,
        "logistician_name": logistician_name,
        "ati_price": ati_price,  # ✅ Теперь записываем рассчитанный ati_price
        "is_published": False,
        "order_type": order_type,
        "bid_price": bid_price,
        "address": address
    })
def delete_old_orders():
    """Удаляет заявки, которых больше нет в TMS"""
    active_external_nos = {order["externalNo"] for order in fetch_orders(ASSIGNED_ORDERS_URL, assigned_payload)}
    
    # Удаляем только те заявки, которых нет среди активных external_no
    deleted_orders = session.query(Order).filter(
        ~Order.external_no.in_(active_external_nos)  # Если external_no не в активных заказах
    ).delete(synchronize_session=False)
    
    session.commit()

    print(f"🗑 Удалено {deleted_orders} неактуальных заявок")

def save_order(order_data):
    """Сохраняем или обновляем данные в таблицу `orders`"""
    existing_order = session.query(Order).filter_by(external_no=order_data["external_no"]).first()

    if existing_order:
        # ✅ Если заявка уже есть, просто обновляем поля
        for key, value in order_data.items():
            setattr(existing_order, key, value)
        print(f"🔄 Обновлена заявка {order_data['external_no']}")
    else:
        # ✅ Если заявки нет, создаем новую
        new_order = Order(**order_data)
        session.add(new_order)
        print(f"➕ Добавлена новая заявка {order_data['external_no']}")

    session.commit()

if __name__ == "__main__":
    process_orders()