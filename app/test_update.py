from app.ati_client import update_cargo
from app.transformers.ati_transformer import prepare_order_for_ati
from app.models import Order
from app.database import SessionLocal

# Открываем сессию БД
db = SessionLocal()

# Выбираем тестовую заявку из БД
selected_order = db.query(Order).filter(Order.external_no == "ТН0001212285").first()

if not selected_order or not selected_order.cargo_id:
    print("❌ Ошибка: заявка ТН0001212285 не найдена в БД или не опубликована в ATI!")
    db.close()
    exit()

# 🔄 Преобразуем `order` в `cargo_data`, как в `publish_cargo()`
cargo_data = prepare_order_for_ati(selected_order)

# 🔄 Добавляем `cargo_id`, так как `prepare_order_for_ati()` его не заполняет
cargo_data["cargo_id"] = selected_order.cargo_id

print("DEBUG cargo_data:", cargo_data)

# Тестируем обновление
update_response = update_cargo(cargo_data)

# Вывод результата
print("Обновление заявки:", update_response)

db.close()