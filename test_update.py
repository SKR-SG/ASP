from app.ati_client import update_cargo
from app.transformers.ati_transformer import prepare_order_for_ati
from app.models import Order
from app.database import SessionLocal

# Открываем сессию БД
db = SessionLocal()

# Выбираем тестовую заявку из БД
selected_order = db.query(Order).filter(Order.external_no == "ТН0001212655").first()

# 🔄 Преобразуем `order` в `cargo_data`, как в `publish_cargo()`
cargo_data = prepare_order_for_ati(selected_order)

print("DEBUG cargo_data:", cargo_data)

# Тестируем обновление
update_response = update_cargo(cargo_data)

# Вывод результата
print("Обновление заявки:", update_response)

db.close()