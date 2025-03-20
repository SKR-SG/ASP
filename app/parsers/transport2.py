import os
import requests
import re
from threading import Timer
from datetime import datetime, timezone
from dotenv import dotenv_values, load_dotenv

# Импорт моделей, логики преобразования и работы с ATI
from app.models import Order, DistributionRule, Platform  
from app.transformers.ati_transformer import prepare_order_for_ati
from app.ati_client import publish_cargo, update_cargo, delete_cargo

# Вместо создания подключения вручную импортируем SessionLocal
from app.database import SessionLocal

# Загружаем переменные окружения
load_dotenv()
env_values = dotenv_values(".env")  # Загружаем .env принудительно

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

# Создаем сессию базы данных через SessionLocal
session = SessionLocal()

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

    delete_old_orders(assigned_orders, auction_orders, free_orders)
    
def extract_street_and_house(address, include_house_number=True):
    """Извлекает улицу и дом из строки адреса.
    
    - `include_house_number=True` → улица + номер дома (для unloading_address).
    - `include_house_number=False` → только улица (для loading_address).
    """

    if not address:
        return None

    # Удаляем текст в скобках (например, "(Екатеринбург)")
    address = re.sub(r"\(.*?\)|\bориентир\b", "", address).strip()  

    # Разбиваем строку на части
    parts = [part.strip() for part in address.split(",")]

    # Ключевые слова для поиска улицы
    street_keywords = ["ул", "улица", "пр-кт", "проспект", "тракт", "шоссе", "ш", "пер", "переулок", "проезд"]

    # Ключевые слова для населенного пункта (чтобы пропустить его и взять следующее поле)
    city_keywords = ["г", "город", "пос", "поселок", "д", "деревня", "пгт", "с", "село", "ст", "станция"]

    street_part = None
    house_number = None
    city_found = False

    # 1️⃣ **Сначала ищем улицу по ключевым словам**
    for part in parts:
        words = part.split()

        if any(word.lower() in street_keywords for word in words):
            # Нашли улицу! Теперь удаляем "ул", "улица" и сохраняем
            street_part = " ".join([word for word in words if word.lower() not in ["ул", "улица"]]).strip()
            break  # Останавливаемся после нахождения первой улицы

    # 2️⃣ **Если улица не найдена, ищем первое поле после города**
    if not street_part:
        for part in parts:
            words = part.split()

            # Если нашли населенный пункт, ставим флаг `city_found`
            if any(word.lower() in city_keywords for word in words):
                city_found = True
                continue

            # Если город найден и следующее поле похоже на улицу → берем его
            if city_found:
                street_part = part
                break

    # Если улица найдена и нужно добавить номер дома
    if include_house_number and street_part:
        for next_part in parts[parts.index(part) + 1:]:
            if re.search(r"\d", next_part):  # Если есть цифра – это номер дома
                house_number = next_part
                break  # Берем первый найденный номер

    # Формируем итоговый результат
    result = f"{street_part} {house_number}" if include_house_number and house_number else street_part

    return result

def process_order(order, order_type):
    """Обрабатываем заказ и сохраняем в БД без преобразования для АТИ"""
    external_no = order.get("externalNo", "N/A")
    existing_order = session.query(Order).filter(Order.external_no == external_no).first()

    # Город погрузки и выгрузки
    loading_place = order.get("loadingPlaces", [{}])[0].get("storagePoint", {})
    unloading_place = order.get("unloadingPlaces", [{}])[0].get("storagePoint", {})
    loading_city = loading_place.get("settlement", "N/A")
    unloading_city = unloading_place.get("settlement", "N/A")

    # Извлекаем адреса
    loading_address = extract_street_and_house(loading_place.get("address"), include_house_number=False)  # ✅ Только улица
    unloading_address = extract_street_and_house(unloading_place.get("address"), include_house_number=True)  # ✅ Улица + дом

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

    # Определение логиста по правилам распределения 
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

    # 🛠 4. Если все еще нет совпадений, ищем **полностью универсальное** правило (`None` и для загрузки, и для выгрузки)
    if not rule:
        rule = session.query(DistributionRule).filter(
            DistributionRule.loading_city.is_(None),
            DistributionRule.unloading_city.is_(None)
        ).first()

    # 🛠 5. Назначаем логиста
    logistician_name = rule.logistician if rule else None

    if not logistician_name:
        print(f"❌ Логист не найден для {loading_city} -> {unloading_city}")

    # Получаем наименование груза по правилам распределения
    cargo_name = rule.cargo_name if rule and rule.cargo_name else "ТНП"

    # Рассчитываем `ati_price`
    ati_price = None
    if rule and bid_price:  # Проверяем, что rule найден и есть цена
        margin_percent = rule.auction_margin_percent if order_type == "AUCTION" else rule.margin_percent
        if margin_percent is not None:
            ati_price = bid_price * (100 - margin_percent) / 100    


    publish_delay = rule.publish_delay if rule and rule.publish_delay else 0

    if existing_order:
        print(f"🔄 Обновление заявки {external_no}")

        # ✅ Проверяем, изменялись ли критические поля
        is_updated = (
            existing_order.load_date != load_date or
            existing_order.unload_date != unload_date or
            existing_order.weight_volume != weight_volume or
            existing_order.vehicle_type != vehicle_type or
            existing_order.loading_types != loading_types or
            existing_order.bid_price != bid_price or  # ✅ Теперь проверяем `bid_price`
            existing_order.loading_city != loading_city or  # ✅ Теперь проверяем `loading_city`
            existing_order.unloading_city != unloading_city or  # ✅ Теперь проверяем `unloading_city`
            existing_order.loading_address != loading_address or  # ✅ Проверяем `loading_address`
            existing_order.unloading_address != unloading_address or  # ✅ Проверяем `unloading_address`
            (existing_order.ati_price != order.get("price") if existing_order.ati_price else False)  # ✅ `ati_price` не перезаписывается, если редактировался вручную
        )

        if existing_order.is_published and rule and rule.auto_publish and is_updated:
            print(f"🚀 Авто-обновление заявки {external_no} в ATI")
            cargo_data = prepare_order_for_ati(existing_order)
            update_cargo(cargo_data)  # ✅ `update_cargo()` выполняется без задержки

        session.commit()
    
    else:
        # ✅ Создание новой заявки
        new_order = Order(
            external_no=external_no,
            platform="Transport2",
            load_date=load_date,
            unload_date=unload_date,
            loading_city=loading_city,  # ✅ Добавили `loading_city`
            unloading_city=unloading_city,  # ✅ Добавили `unloading_city`
            weight_volume=weight_volume,
            vehicle_type=vehicle_type,
            loading_types=loading_types,
            comment=comment,
            cargo_name=cargo_name,
            logistician_name=logistician_name,
            ati_price=order.get("price"),
            is_published=False,
            order_type=order_type,
            bid_price=bid_price,
            loading_address=loading_address,  # ✅ Теперь только улица
            unloading_address=unloading_address  # ✅ Теперь улица + дом
        )
        session.add(new_order)
        session.commit()
        print(f"➕ Добавлена новая заявка {external_no}")

        if rule:
            # Выбираем авто-публикацию в зависимости от типа заявки
            auto_publish_flag = rule.auto_publish_auction if order_type == "AUCTION" else rule.auto_publish
            if auto_publish_flag:
                print(f"🚀 Авто-публикация заявки {external_no} через {publish_delay} минут.")
                if publish_delay == 0:
                    publish_now(external_no)
                else:
                    Timer(publish_delay * 60, publish_now, args=[external_no]).start()

def publish_now(external_no):
    """Публикует заявку в ATI, если она есть в БД"""
    order = session.query(Order).filter(Order.external_no == external_no).first()
    
    if not order:
        print(f"⚠️ Ошибка: Заявка {external_no} не найдена в БД, публикация отменена.")
        return

    cargo_data = prepare_order_for_ati(order)
    response = publish_cargo(cargo_data)

    if response and "cargo_id" in response:
        order.cargo_id = response["cargo_id"]
        order.is_published = response["cargo_number"]
        session.commit()
        print(f"✅ Заявка {external_no} успешно опубликована в ATI: {response['cargo_number']}")
    else:
        print(f"❌ Ошибка публикации заявки {external_no}.")

def delete_old_orders(assigned_orders, auction_orders, free_orders):
    """Удаляет заявки, которых больше нет в TMS"""

    active_external_nos = {
        order["externalNo"] for order in assigned_orders + auction_orders + free_orders
    }

    db_orders = session.query(Order).all()  
    to_delete = [order for order in db_orders if order.external_no not in active_external_nos]

    if not to_delete:
        print("✅ Нет заявок для удаления.")
        return

    for order in to_delete:
        if order.cargo_id:
            print(f"🗑 Удаляем заявку {order.external_no} из ATI")
            delete_cargo(order)  # ✅ Теперь передаем `order` целиком

        session.delete(order)  # ✅ Теперь безопасно удаляем из БД

    session.commit()
    print(f"🗑 Удалено {len(to_delete)} неактуальных заявок")

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

def is_platform_enabled(platform_name: str) -> bool:
    db = SessionLocal()
    platform = db.query(Platform).filter(Platform.name == platform_name).first()
    db.close()
    return platform.enabled if platform else False

if __name__ == "__main__":
    if is_platform_enabled("Transport2"):
        process_orders()  # Ваша функция парсинга
    else:
        print("Площадка transport2 отключена, парсинг не выполняется.") 