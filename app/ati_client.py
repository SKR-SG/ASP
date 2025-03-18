import json
import os
import requests
import time
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models import Logist, Order  # Исправленный импорт
from app.database import SessionLocal

# Загружаем переменные окружения
load_dotenv()

# Настройка подключения к БД
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

ATI_API_BASE_URL = "https://api.ati.su"
ATI_API_TOKEN = os.getenv("ATI_API_TOKEN")  # Используем правильный токен!

HEADERS = {
    "Authorization": f"Bearer {ATI_API_TOKEN}",
    "Content-Type": "application/json"
}

def get_car_types():
    """Получает словарь типов кузовов с ATI"""
    url = f"{ATI_API_BASE_URL}/v1.0/dictionaries/carTypes"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        car_types = response.json()
        return {item["Name"].lower(): item["TypeId"] for item in car_types}
    print(f"❌ Ошибка запроса carTypes: {response.status_code}, {response.text}")
    return {}

def get_loading_types():
    """Получает словарь способов загрузки с ATI"""
    url = f"{ATI_API_BASE_URL}/v1.0/dictionaries/loadingTypes"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        loading_types = response.json()
        return {item["Name"].lower(): item["Id"] for item in loading_types}
    print(f"❌ Ошибка запроса loadingTypes: {response.status_code}, {response.text}")
    return {}

def get_unloading_types():
    """Получает словарь способов разгрузки с ATI"""
    url = f"{ATI_API_BASE_URL}/v1.0/dictionaries/unloadingTypes"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        unloading_types = response.json()
        return {item["Name"].lower(): item["Id"] for item in unloading_types}
    print(f"❌ Ошибка запроса unloadingTypes: {response.status_code}, {response.text}")
    return {}

def get_city_id(city_name):
    """Получает ID города по названию через API ATI."""
    url = f"{ATI_API_BASE_URL}/gw/gis-dict/v1/autocomplete/suggestions"
    payload = {
        "prefix": city_name,
        "suggestion_types": 1,  
        "limit": 1,
        "country_id": 1  
    }

    response = requests.post(url, json=payload, headers=HEADERS)
    data = response.json()
    
    if response.status_code == 200 and "suggestions" in data and data["suggestions"]:
        city_id = data["suggestions"][0]["city"]["id"]
        print(f"✅ Найден ID города {city_name}: {city_id}")
        return city_id
    else:
        print(f"🚨 Ошибка: не найден ID для города {city_name}")
        return None

def get_contact_id(logist_name):
    """Получает ID логиста из БД или API ATI."""
    session = SessionLocal()
    logist = session.query(Logist).filter(Logist.name.ilike(f"%{logist_name}%")).first()
    session.close()

    if logist:
        print(f"✅ Найден ID логиста {logist.name} в БД: {logist.contact_id}")
        return logist.contact_id

    # Запрашиваем API ATI
    url = f"{ATI_API_BASE_URL}/v1.0/firms/contacts"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        contacts = response.json()
        for contact in contacts:
            if logist_name.lower() in contact["name"].lower():
                return contact["id"]
    
    print(f"❌ Логист {logist_name} не найден в ATI!")
    return None

def publish_cargo(cargo_data):
    """Публикует груз в ATI и сохраняет cargo_id и cargo_number в БД"""
    url = f"{ATI_API_BASE_URL}/v2/cargos"

        # Проверяем, все ли ID переданы
    if not cargo_data["loading_city_id"] or not cargo_data["unloading_city_id"]:
        return {"error": "Ошибка: не определены ID городов"}

    if cargo_data["logist_id"] is None or cargo_data["logist_id"] == "":
        return {"error": "Ошибка: не определен ID логиста"}

    # 🆕 Исправленная передача `load_date`
    load_dates = {
        "type": "from-date",
        "time": {
            "type": "bounded",
            "start": cargo_data["loading_dates"]["time"]["start"],
            "end": cargo_data["loading_dates"]["time"]["end"],
            "offset": "+00:00"
        },
        "first_date": cargo_data["loading_dates"]["first_date"],
        "last_date": cargo_data["loading_dates"]["last_date"]
    }

    # 🆕 Исправленная передача `unload_date`
    unload_dates = {
        "first_date": cargo_data["unloading_dates"]["first_date"],
        "last_date": cargo_data["unloading_dates"]["last_date"],
        "time": {
            "type": "bounded" if cargo_data["unloading_dates"]["time"]["start"] else "round-the-clock",
            "start": cargo_data["unloading_dates"]["time"]["start"],
            "end": cargo_data["unloading_dates"]["time"]["end"],
            "offset": "+00:00"
        }
    } if cargo_data["unloading_dates"]["first_date"] else None  # Если нет даты, не передаем

    # 🆕 Формируем структуру `truck`
    truck_data = {
        "load_type": "ftl",
        "body_types": cargo_data["body_types"],
        "body_loading": {"types": cargo_data["body_loading"], "is_all_required": True},
        "body_unloading": {"types": cargo_data["body_unloading"], "is_all_required": True}
    }

    # Формируем запрос на публикацию
    payload = {
        "cargo_application": {
            "route": {
                "loading": {
                    "city_id": cargo_data["loading_city_id"],
                    "address": cargo_data["loading_address"],
                    "dates": load_dates,  # 🆕 Передаем исправленные даты
                    "cargos": [
                        {
                            "id": 1,
                            "name": cargo_data["cargo_name"],
                            "weight": {"type": "tons", "quantity": cargo_data["weight"]},
                            "volume": {"quantity": cargo_data["volume"]}
                        }
                    ]
                },
                "unloading": {
                    "city_id": cargo_data["unloading_city_id"],
                    "address": cargo_data["unloading_address"],
                    "dates": unload_dates  # 🆕 Передаем даты разгрузки (если есть)
                } if unload_dates else {"city_id": cargo_data["unloading_city_id"], "address": cargo_data["unloading_address"]}  # Не передаем пустой блок
            },
            "truck": truck_data,  # 🆕 Теперь `truck` формируется тут
            "payment": cargo_data["payment"],
            "boards": [{"id": "a0a0a0a0a0a0a0a0a0a0a0a0", "publication_mode": "now"}],
            "note": cargo_data["note"],
            "contacts": [cargo_data["logist_id"]],
        }
    }

    response = requests.post(url, json=payload, headers=HEADERS)

    if response.status_code == 200:
        data = response.json()
        cargo_id = data["cargo_application"]["cargo_id"]
        cargo_number = data["cargo_application"]["cargo_number"]
        print(f"✅ Груз опубликован! ID: {cargo_id}, Номер: {cargo_number}")
        
    
        
        # Обновляем БД
        db = SessionLocal()
        order = db.query(Order).filter(Order.external_no == cargo_data["external_id"]).first()
        if order:
            order.cargo_id = str(cargo_id)  # 🛠️ Приводим к строке
            order.is_published = str(cargo_number)  # 🛠️ Приводим к строке
            db.commit()
        db.close()    
        
        return {"cargo_id": cargo_id, "cargo_number": cargo_number}

    print(f"❌ Ошибка публикации: {response.status_code}, {response.text}")
    return response.json()

def update_cargo(cargo_data):
    """Обновляет заявку груза на ATI"""
    
    if not cargo_data["cargo_id"]:
        print(f"❌ Ошибка: У груза {cargo_data['external_id']} нет cargo_id, обновление невозможно.")
        return {"error": "cargo_id отсутствует, обновление невозможно"}

    url = f"{ATI_API_BASE_URL}/v2/cargos/{cargo_data['cargo_id']}"

        # Проверяем, все ли ID переданы
    if not cargo_data["loading_city_id"] or not cargo_data["unloading_city_id"]:
        return {"error": "Ошибка: не определены ID городов"}

    if cargo_data["logist_id"] is None or cargo_data["logist_id"] == "":
        return {"error": "Ошибка: не определен ID логиста"}

    # 🆕 Исправленная передача `load_date`
    load_dates = {
        "type": "from-date",
        "time": {
            "type": "bounded",
            "start": cargo_data["loading_dates"]["time"]["start"],
            "end": cargo_data["loading_dates"]["time"]["end"],
            "offset": "+00:00"
        },
        "first_date": cargo_data["loading_dates"]["first_date"],
        "last_date": cargo_data["loading_dates"]["last_date"]
    }

    # 🆕 Исправленная передача `unload_date`
    unload_dates = {
        "first_date": cargo_data["unloading_dates"]["first_date"],
        "last_date": cargo_data["unloading_dates"]["last_date"],
        "time": {
            "type": "bounded" if cargo_data["unloading_dates"]["time"]["start"] else "round-the-clock",
            "start": cargo_data["unloading_dates"]["time"]["start"],
            "end": cargo_data["unloading_dates"]["time"]["end"],
            "offset": "+00:00"
        }
    } if cargo_data["unloading_dates"]["first_date"] else None  # Если нет даты, не передаем

    # 🆕 Формируем структуру `truck`
    truck_data = {
        "load_type": "ftl",
        "body_types": cargo_data["body_types"],
        "body_loading": {"types": cargo_data["body_loading"], "is_all_required": True},
        "body_unloading": {"types": cargo_data["body_unloading"], "is_all_required": True}
    }

    # Формируем запрос на публикацию
    payload = {
        "cargo_application": {
            "route": {
                "loading": {
                    "city_id": cargo_data["loading_city_id"],
                    "address": cargo_data["loading_address"],
                    "dates": load_dates,  # 🆕 Передаем исправленные даты
                    "cargos": [
                        {
                            "id": 1,
                            "name": cargo_data["cargo_name"],
                            "weight": {"type": "tons", "quantity": cargo_data["weight"]},
                            "volume": {"quantity": cargo_data["volume"]}
                        }
                    ]
                },
                "unloading": {
                    "city_id": cargo_data["unloading_city_id"],
                    "address": cargo_data["unloading_address"],
                    "dates": unload_dates  # 🆕 Передаем даты разгрузки (если есть)
                } if unload_dates else {"city_id": cargo_data["unloading_city_id"], "address": cargo_data["unloading_address"]}  # Не передаем пустой блок
            },
            "truck": truck_data,  # 🆕 Теперь `truck` формируется тут
            "payment": cargo_data["payment"],
            "boards": [{"id": "a0a0a0a0a0a0a0a0a0a0a0a0", "publication_mode": "now"}],
            "note": cargo_data["note"],
            "contacts": [cargo_data["logist_id"]],
        }
    }

    response = requests.put(url, json=payload, headers=HEADERS)

    if response.status_code == 200:
        print(f"✅ Груз {cargo_data['cargo_id']} ({cargo_data['external_id']}) обновлен успешно!")
        return response.json()

    elif response.status_code == 429:
        print(f"⚠️ Ошибка 429. Превышен суточный лимит запросов (5000) для контакта. Дальнейшие запросы невозможны в течение 24 часов.")
        return {"error": "Превышен суточный лимит запросов (5000) для контакта"}

    else:
        print(f"❌ Ошибка обновления {cargo_data['cargo_id']}: {response.status_code}, {response.text}")
        return response.json()

def delete_cargo(order):
    """Удаляет заявку груза на ATI"""
    if not order.cargo_id:
        print(f"❌ Ошибка: У заявки {order.external_no} нет cargo_id, удаление невозможно.")
        return {"error": "cargo_id отсутствует, удаление невозможно"}

    url = f"{ATI_API_BASE_URL}/v1.0/loads/{order.cargo_id}"

    response = requests.delete(url, headers=HEADERS)

    if response.status_code == 200:
        print(f"✅ Груз {order.cargo_id} ({order.external_no}) удален успешно!")

        # Обновляем БД
        db = SessionLocal()
        order_in_db = db.query(Order).filter(Order.external_no == order.external_no).first()
        if order_in_db:
            order_in_db.cargo_id = None
            order_in_db.is_published = None
            db.commit()
        db.close()

        return response.json()
    else:
        print(f"❌ Ошибка удаления {order.cargo_id}: {response.status_code}, {response.text}")
        return response.json()
