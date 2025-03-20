from app.ati_client import delete_cargo
from app.models import Order
from app.database import SessionLocal

# Открываем сессию БД
db = SessionLocal()

# Выбираем тестовую заявку из БД
selected_order = db.query(Order).filter(Order.external_no == "ТН0001212655").first()

if not selected_order or not selected_order.cargo_id:
    print("❌ Ошибка: заявка ТН0001212655 не найдена в БД или не опубликована в ATI!")
    db.close()
    exit()

# Тестируем удаление
delete_response = delete_cargo(selected_order)

# Вывод результата
print("Удаление заявки:", delete_response)

db.close()
