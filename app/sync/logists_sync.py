import os
import requests
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Logist
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация API
ATI_API_TOKEN = os.getenv("ATI_API_TOKEN")
ATI_API_BASE_URL = "https://api.ati.su"

HEADERS = {
    "Authorization": f"Bearer {ATI_API_TOKEN}",
    "Content-Type": "application/json"
}

def fetch_logists_from_ati():
    """Запрашивает список логистов с ATI"""
    url = f"{ATI_API_BASE_URL}/v1.0/firms/contacts"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"❌ Ошибка запроса к ATI: {response.status_code}")
        return []

    return response.json()  # Возвращает список логистов

def sync_logists(db: Session):
    """Обновляет таблицу логистов в БД на основе данных ATI"""
    logists_from_ati = fetch_logists_from_ati()

    if not logists_from_ati:
        print("⚠️ Не удалось получить данные логистов с ATI")
        return

    for ati_logist in logists_from_ati:
        name = ati_logist.get("name", "").strip()
        contact_id = ati_logist.get("contact_id", 0)

        if not name:
            print(f"⚠️ Пропускаем логиста без имени: {ati_logist}")
            continue  # Пропускаем записи без имени

        print(f"DEBUG: Загружен логист {name} с contact_id={contact_id}")

        # Проверяем, есть ли уже такой логист в БД
        existing_logist = db.query(Logist).filter(Logist.contact_id == contact_id).first()

        if existing_logist:
            existing_logist.name = name  # Обновляем имя логиста
        else:
            new_logist = Logist(name=name, contact_id=contact_id)
            db.add(new_logist)

    db.commit()
    print(f"✅ Синхронизация логистов завершена. Обновлено логистов: {len(logists_from_ati)}")

def run_logists_sync():
    """Запускает процесс синхронизации логистов"""
    db = SessionLocal()
    try:
        sync_logists(db)
    finally:
        db.close()

if __name__ == "__main__":
    run_logists_sync()
