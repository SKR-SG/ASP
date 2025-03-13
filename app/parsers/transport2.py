import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base

# Загружаем переменные окружения
load_dotenv()
T2_API_TOKEN = os.getenv("T2_API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Проверка переменной окружения T2_API_TOKEN
if not T2_API_TOKEN:
    print("❌ Ошибка: T2_API_TOKEN не задан!")
    exit()

# Настройка подключения к БД
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_no = Column(String, unique=True, nullable=False, index=True)  # Внешний номер заявки
    loading_city = Column(String, nullable=False)  # Город загрузки
    unloading_city = Column(String, nullable=False)  # Город выгрузки
    loading_datetime = Column(DateTime, nullable=False)
    unloading_datetime = Column(DateTime, nullable=True)
    weight = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    loading_types = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    factory_bid = Column(Float, nullable=True)
    last_bet = Column(Float, nullable=True)
    status = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=True)

# Создание таблицы в БД
Base.metadata.create_all(engine)

# Заголовки для запроса
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Authorization": f"Token {T2_API_TOKEN}",  # Используем токен из .env
}

# URL API для заявок
assigned_orders_url = "https://api.transport2.ru/carrier/graphql?operation=assignedOrders"
auction_orders_url = "https://api.transport2.ru/carrier/graphql?operation=auctionNewOrders"
free_orders_url = "https://api.transport2.ru/carrier/graphql?operation=freeOrders"  # Новый URL

# Тело запроса для заявок со статусом ASSIGNED
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
                vehicleRequirements {  # Добавляем vehicleRequirements
                    name
                    bodySubtype {
                        name
                    }
                }
            }
        }
    """
}

# Тело запроса для аукционных заявок
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
                vehicleRequirements {  # Добавляем vehicleRequirements
                    name
                    bodySubtype {
                        name
                    }
                }
            }
        }
    """
}

# Тело запроса для заявок со статусом FREE
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
                vehicleRequirements {  # Добавляем vehicleRequirements
                    name
                    bodySubtype {
                        name
                    }
                }
            }
        }
    """
}

def clean_city_name(city):
    """Очищает и нормализует название города."""
    return city.replace("г.", "").replace("город", "").strip()

def extract_city(storage_point):
    """Извлекает название города из storage_point."""
    settlement = storage_point.get('settlement', '').strip()
    if settlement:
        return clean_city_name(settlement)
    
    address = storage_point.get('address', '')
    if address:
        parts = address.split(', ')
        if len(parts) >= 5:
            city = parts[4]
            return clean_city_name(city)
    
    return "N/A"

def fetch_and_process_orders(url, payload, is_auction=False, is_free=False):
    """Получает и обрабатывает заказы с API."""
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при выполнении запроса: {e}")
        return [], []
    except ValueError:
        print("❌ Ошибка: Получен некорректный JSON")
        return [], []

    orders = data['data']['assignedOrders'] if not is_auction and not is_free else \
             data['data']['auctionOrders'] if is_auction else \
             data['data']['freeOrders']
    current_datetime = datetime.now(timezone.utc)

    processed_orders = []
    external_nos = []

    for order in orders:
        if is_auction:
            status = order.get('status')
            auction_status = order.get('lot', {}).get('auctionStatus')
            if status != "FREE" or auction_status != "ACTIVE":
                continue
            display_status = "Аукцион"
            factory_bid = order.get('lot', {}).get('startPrice')
            last_bet = order.get('lot', {}).get('lastBet')
        elif is_free:
            if order.get('status') != "FREE":
                continue
            display_status = "Свободная"
            factory_bid = order.get('price')
            last_bet = None
        else:
            if order.get('status') != "ASSIGNED":
                continue
            display_status = "Назначена"
            factory_bid = order.get('price')
            last_bet = None

        loading_datetime_str = order.get('loadingDatetime')
        if loading_datetime_str:
            try:
                loading_datetime = datetime.fromisoformat(loading_datetime_str)
            except ValueError:
                print(f"❌ Ошибка формата даты: {loading_datetime_str}")
                continue
        else:
            continue

        if loading_datetime < current_datetime:
            continue

        external_no = order.get('externalNo', 'N/A')
        external_nos.append(external_no)

        loading_place = order.get('loadingPlaces', [{}])[0].get('storagePoint', {})
        loading_city = extract_city(loading_place)

        unloading_place = order.get('unloadingPlaces', [{}])[0].get('storagePoint', {})
        unloading_city = extract_city(unloading_place)

        unloading_datetime = order.get('unloadingDatetime', 'N/A')
        weight = order.get('weight')
        volume = order.get('volume')
        loading_types = order.get('loadingTypes', 'N/A')
        comment = order.get('comment', 'N/A')
        vehicle_requirements = order.get('vehicleRequirements', {})
        vehicle_type = vehicle_requirements.get('name', 'N/A')

        processed_orders.append({
            "Внеш.№": external_no,
            "Место погрузки": loading_city,
            "Место доставки": unloading_city,
            "Дата погрузки": loading_datetime_str,
            "Дата доставки": unloading_datetime,
            "Вес (т)": weight,
            "Объём (м³)": volume,
            "Типы погрузки / разгрузки": loading_types,
            "Комментарий": comment,
            "Ставка завода": factory_bid,
            "Последняя ставка": last_bet,
            "Статус": display_status,
            "Тип ТС": vehicle_type,
        })
    
    return processed_orders, external_nos

def delete_old_orders(external_nos):
    """Удаляет устаревшие заказы, которых нет в текущем ответе API."""
    try:
        session.query(Order).filter(Order.external_no.notin_(external_nos)).delete(synchronize_session=False)
        session.commit()
        print(f"Удалено устаревших заказов.")
    except Exception as e:
        print(f"Ошибка при удалении устаревших заказов: {e}")

def save_order_to_db(order):
    """Добавляет или обновляет заказ в БД."""
    existing_order = session.query(Order).filter_by(external_no=order["Внеш.№"]).first()
    
    if existing_order:
        print(f"🔄 Обновление заказа {order['Внеш.№']} в БД")
        existing_order.loading_city = order["Место погрузки"]
        existing_order.unloading_city = order["Место доставки"]
        existing_order.loading_datetime = order["Дата погрузки"]
        existing_order.unloading_datetime = order["Дата доставки"]
        existing_order.weight = order["Вес (т)"]
        existing_order.volume = order["Объём (м³)"]
        existing_order.loading_types = order["Типы погрузки / разгрузки"]
        existing_order.comment = order["Комментарий"]
        existing_order.factory_bid = order["Ставка завода"]
        existing_order.last_bet = order["Последняя ставка"]
        existing_order.status = order["Статус"]
        existing_order.vehicle_type = order["Тип ТС"]
    else:
        print(f"✅ Добавление нового заказа {order['Внеш.№']} в БД")
        new_order = Order(
            external_no=order["Внеш.№"],
            loading_city=order["Место погрузки"],
            unloading_city=order["Место доставки"],
            loading_datetime=order["Дата погрузки"],
            unloading_datetime=order["Дата доставки"],
            weight=order["Вес (т)"],
            volume=order["Объём (м³)"],
            loading_types=order["Типы погрузки / разгрузки"],
            comment=order["Комментарий"],
            factory_bid=order["Ставка завода"],
            last_bet=order["Последняя ставка"],
            status=order["Статус"],
            vehicle_type=order["Тип ТС"]
        )
        session.add(new_order)
    
    session.commit()

# Основной код (разовый запуск)
print(f"Запуск обновления данных: {datetime.now()}")

# Получаем и обрабатываем заявки
assigned_orders, assigned_external_nos = fetch_and_process_orders(assigned_orders_url, assigned_payload)
auction_orders, auction_external_nos = fetch_and_process_orders(auction_orders_url, auction_payload, is_auction=True)
free_orders, free_external_nos = fetch_and_process_orders(free_orders_url, free_payload, is_free=True)

# Объединяем заявки и внешние номера
all_orders = assigned_orders + auction_orders + free_orders
all_external_nos = assigned_external_nos + auction_external_nos + free_external_nos

# Выводим информацию
for order in all_orders:
    print(f"Внеш.№: {order['Внеш.№']}")
    print(f"Место погрузки: {order['Место погрузки']}")
    print(f"Место доставки: {order['Место доставки']}")
    print(f"Дата погрузки: {order['Дата погрузки']}")
    print(f"Дата доставки: {order['Дата доставки']}")
    print(f"Вес (т): {order['Вес (т)']}")
    print(f"Объём (м³): {order['Объём (м³)']}")
    print(f"Типы погрузки / разгрузки: {order['Типы погрузки / разгрузки']}")
    print(f"Комментарий: {order['Комментарий']}")
    print(f"Ставка завода: {order['Ставка завода']}")
    print(f"Последняя ставка: {order['Последняя ставка']}")
    print(f"Статус: {order['Статус']}")
    print(f"Тип ТС: {order['Тип ТС']}")
    print("-" * 40)  # Разделитель между заявками

# Сохраняем каждую заявку в базу данных
for order in all_orders:
    save_order_to_db(order)

# Удаляем устаревшие заявки
delete_old_orders(all_external_nos)