from app.ati_client import publish_cargo
from app.transformers.ati_transformer import prepare_order_for_ati
from app.models import Order
from app.database import SessionLocal

# Открываем сессию БД
db = SessionLocal()

# Выбираем тестовую заявку из БД
selected_order = db.query(Order).filter(Order.external_no == "ТН0001211868").first()

if not selected_order:
    print("❌ Ошибка: заявка ТН0001211868 не найдена в БД!")
    db.close()
    exit()

# Преобразуем данные в формат ATI
cargo_data = prepare_order_for_ati(selected_order)

print("DEBUG cargo_data:", cargo_data)

# Публикуем заявку
ati_response = publish_cargo(cargo_data)

# Вывод результата
print(ati_response)

db.close()
