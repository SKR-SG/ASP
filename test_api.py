import asyncio
import httpx

BASE_URL = "http://localhost:8000/orders"

async def test_publish(order_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/{order_id}/publish")
        print("Publish:", response.json())

async def test_update(order_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/{order_id}/update")
        print("Update:", response.json())

async def test_delete(order_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/{order_id}/delete")
        print("Delete:", response.json())

async def test_update_price(order_id: int, new_price: float):
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{BASE_URL}/{order_id}/price", 
            json={"new_price": new_price}
        )
        print("Price Update:", response.json())

async def main():
    order_id = 48  # Укажите тестовый идентификатор заявки
    # Тест обновления цены — изменение происходит только в БД
    await test_update_price(order_id, 1500.0)
    
    # Если нужно обновить данные на ATI, вызывайте принудительно /update
    await test_update(order_id)
    
    # Пример вызова публикации и удаления:
    # await test_publish(order_id)
    # await test_delete(order_id)

if __name__ == "__main__":
    asyncio.run(main())
