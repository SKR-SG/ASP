import os
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models import Logist, Base  # Исправленный импорт

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
    # 1️⃣ Проверяем в БД
    logist = session.query(Logist).filter(Logist.name.ilike(f"%{logist_name}%")).first()
    if logist:
        print(f"✅ Найден ID логиста {logist.name} в БД: {logist.contact_id}")
        return logist.contact_id
    
    # 2️⃣ Запрашиваем API ATI
    url = f"{ATI_API_BASE_URL}/v1.0/firms/contacts"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        contacts = response.json()
        for contact in contacts:
            if logist_name.lower() in contact["name"].lower():
                new_logist = Logist(name=contact["name"], contact_id=contact["id"])  # Исправлено
                session.add(new_logist)
                session.commit()
                print(f"✅ Добавлен логист {contact['name']} в БД, ID: {contact['id']}")
                return contact["id"]
    
    print(f"❌ Логист {logist_name} не найден!")
    return None

def publish_cargo(cargo_data):
    """Публикует груз в ATI.SU."""
    url = f"{ATI_API_BASE_URL}/v2/cargos"

    # Получаем ID городов загрузки и выгрузки
    loading_city_id = get_city_id(cargo_data["loading_city"])
    unloading_city_id = get_city_id(cargo_data["unloading_city"])

    if not loading_city_id or not unloading_city_id:
        return {"error": "Ошибка определения ID города"}

    # Получаем ID логиста
    logist_id = get_contact_id(cargo_data["logist"])
    if logist_id is None:
        return {"error": "Ошибка определения ID логиста"}

    # Формируем запрос на публикацию
    payload = {
        "cargo_application": {
            "external_id": str(cargo_data["external_id"]),
            "route": {
                "loading": {
                    "city_id": loading_city_id,
                    "address": cargo_data["loading_address"],
                    "dates": {
                        "type": "ready",
                        "time": {"type": "round-the-clock"},
                        "is_available_tomorrow": False
                    },
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
                    "city_id": unloading_city_id,
                    "address": cargo_data["unloading_address"]
                }
            },
            "truck": {
                "load_type": "ftl",
                "body_types": [200],
                "body_loading": {"types": [8], "is_all_required": True},
                "body_unloading": {"types": [8], "is_all_required": True}
            },
            "payment": {
                "type": "rate-request",
                "hide_counter_offers": True,
                "direct_offer": True,
                "payment_mode": {
                    "type": "delayed-payment",
                    "payment_delay_days": 30
                },
                "currency_type": 1,
                "rate_with_vat_available": True,
                "rate_without_vat_available": True
            },
            "boards": [{"id": "a0a0a0a0a0a0a0a0a0a0a0a0", "publication_mode": "now"}],
            "note": cargo_data.get("note", "Автоматическая публикация"),
            "contacts": [logist_id]
        }
    }

    response = requests.post(url, json=payload, headers=HEADERS)

    if response.status_code == 200:
        data = response.json()
        cargo_id = data["cargo_application"]["cargo_id"]
        cargo_number = data["cargo_application"]["cargo_number"]
        print(f"✅ Груз опубликован! ID: {cargo_id}, Номер: {cargo_number}")
        return {"cargo_id": cargo_id, "cargo_number": cargo_number}

    print(f"❌ Ошибка публикации: {response.status_code}")
    return response.json()

# 🔹 **Тестовые данные**
test_cargo = {
    "external_id": "test_001",
    "loading_city": "Челябинск",
    "loading_address": "ул. Тверская, д. 1",
    "unloading_city": "Аскино",
    "unloading_address": "ул Ленина, дом 5",
    "cargo_name": "Стройматериалы",
    "weight": 20,
    "volume": 90,
    "note": "тестовая отправка",
    "logist": "Сергей"
}

