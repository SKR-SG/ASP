import os
import requests
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from app.models import Request, DistributionRule  # Импорт моделей
from app.ati_client import publish_cargo  # Импорт публикации в АТИ
from app.ati_client import get_city_id  # Импорт функции для получения ID города
from app.distribution_rules import distribute_order  # Импорт функции распределения

# Загружаем переменные окружения
load_dotenv()

# API URL и Токен
T2_API_TOKEN = os.getenv("T2_API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not T2_API_TOKEN:
    print("❌ Ошибка: T2_API_TOKEN не задан!")
    exit()

HEADERS = {
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

def fetch_orders(url, payload):
    """Запрашивает заявки из TMS API и возвращает отфильтрованные данные"""
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json().get("data", {})
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса {url}: {e}")
        return {}

def process_orders():
    """Основная функция обработки заявок"""
    assigned_orders = fetch_orders(ASSIGNED_ORDERS_URL, assigned_payload).get("assignedOrders", [])
    auction_orders = fetch_orders(AUCTION_ORDERS_URL, auction_payload).get("auctionOrders", [])
    free_orders = fetch_orders(FREE_ORDERS_URL, free_payload).get("freeOrders", [])

    # **Применяем фильтрацию перед обработкой**
    assigned_orders = filter_valid_orders(assigned_orders, "ASSIGNED")
    auction_orders = filter_valid_orders(auction_orders, "AUCTION")
    free_orders = filter_valid_orders(free_orders, "FREE")

    all_orders = (
        [(order, "ASSIGNED") for order in assigned_orders] +
        [(order, "AUCTION") for order in auction_orders] +
        [(order, "FREE") for order in free_orders]
    )

    print(f"✅ Обработано заявок: {len(all_orders)}")
    for order, order_type in all_orders:
        process_order(order, order_type)  # 🔹 Теперь передаём `order_type`
    
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

def process_order(order, order_type):
    """Обрабатывает каждую заявку после фильтрации"""
    external_no = order.get("externalNo", "N/A")

    # Город погрузки и разгрузки
    loading_place = order.get("loadingPlaces", [{}])[0].get("storagePoint", {})
    unloading_place = order.get("unloadingPlaces", [{}])[0].get("storagePoint", {})
    loading_city = loading_place.get("settlement", "N/A")
    unloading_city = unloading_place.get("settlement", "N/A")

    # Даты
    load_date = order.get("loadingDatetime", "N/A")
    unload_date = order.get("unloadingDatetime", "N/A")
    
    # Вес и объем
    weight = order.get("weight", 0)
    volume = order.get("volume", 0)
    weight_volume = f"{weight} т / {volume} м³"

    vehicle_type = order.get("vehicleRequirements", {}).get("name", "N/A") # Тип ТС
    loading_types = order.get("loadingTypes", "N/A")  # Типы погрузки/разгрузки
    comment = order.get("comment", "N/A")  # Комментарий к заявке
    
     # Ставка завода и последняя ставка
    factory_bid = order.get("price", 0) if order_type in ["ASSIGNED", "FREE"] else None
    last_bet = order.get("lot", {}).get("lastBet", None) if order_type == "AUCTION" else None
    
    # Если заявка аукционная, используем только `last_bet`, иначе `factory_bid`
    bid_price = last_bet if last_bet else factory_bid

    # Получаем ID города загрузки
    loading_city_id = get_city_id(order.get("loading_city", ""))
    unloading_city_id = get_city_id(order.get("unloading_city", ""))

    if loading_city_id is None or unloading_city_id is None:
        print(f"❌ Ошибка: не найден ID для города загрузки {order.get('loading_city')} или выгрузки {order.get('unloading_city')}")
        return  # Пропускаем заявку, если города не найдены

    # Наименование груза по правилам распределения
    cargo_name = session.query(DistributionRule.cargo_name).filter_by(
        loading_city_id=loading_city_id, unloading_city_id=unloading_city_id
    ).scalar()

    # Получаем правило распределения для данного маршрута
#    distribution = distribute_order({
#        "loading_city_id": loading_city_id,
#        "unloading_city_id": unloading_city_id,
#        "factory_bid": factory_rate,
#        "auction_bid": auction_rate
#    }, session)

    # Назначаем логиста и ATI-цену из найденного правила
#    logist_id = distribution["logist_id"] if distribution else None
#    ati_price = distribution["ati_price"] if distribution else None
      
    # Получаем маржу для обычных и аукционных заявок
    margin_percent = session.query(DistributionRule.margin_percent).filter_by(
        loading_city_id=loading_city_id, unloading_city_id=unloading_city_id
    ).scalar() or 0  # Если нет правила, ставим 0%

    auction_margin_percent = session.query(DistributionRule.auction_margin_percent).filter_by(
        loading_city_id=loading_city_id, unloading_city_id=unloading_city_id
    ).scalar() or 0  # Если нет правила, ставим 0%

     # Извлекаем ставки
    rate_factory = order.get("price", 0)  # Ставка завода
    rate_auction = order.get("lot", {}).get("lastBet", 0)  # Последняя ставка аукциона

     # Рассчитываем `ati_price`
    ati_price = None
    if order_type == "AUCTION":
        ati_price = last_bet * (100 - auction_margin_percent) / 100 if auction_margin_percent else None
    else:
        ati_price = factory_bid * (100 - margin_percent) / 100 if margin_percent else None

    # Получаем ID логиста
    logist_id = session.query(DistributionRule.logist_id).filter_by(
        loading_city_id=loading_city_id, unloading_city_id=unloading_city_id
    ).scalar()

    # Если логист не найден, назначаем логиста по умолчанию
    if logist_id is None:
        print(f"⚠️ Груз {external_no} не попал под правило. Назначаем логиста по умолчанию.")
        logist_id = 1  # <-- Указываем ID логиста по умолчанию

    # Сохраняем в БД
    save_request({
        "external_no": external_no,
        "platform": "TMS",
        "load_date": load_date,
        "loading_city_id": loading_city_id,
        "unloading_city_id": unloading_city_id,
        "unload_date": unload_date,
        "weight_volume": weight_volume,
        "vehicle_type": vehicle_type,
        "loading_types": loading_types,
        "comment": comment,
        "cargo_name": cargo_name,
        "logistician_id": logist_id,
        "ati_price": ati_price,
        "is_published": False,
        "order_type": order_type,
        "bid_price": bid_price  # 🔹 Итоговая ставка (ставка завода или последняя ставка аукциона)
    })

def save_request(request_data):
    """Сохраняем заявку в БД"""
    existing_request = session.query(Request).filter_by(external_no=request_data["external_no"]).first()
    
    if existing_request:
        for key, value in request_data.items():
            setattr(existing_request, key, value)
    else:
        new_request = Request(**request_data)
        session.add(new_request)

    session.commit()

if __name__ == "__main__":
    process_orders()