from fastapi import FastAPI
from app.routes import users, orders  # Измените requests на orders

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])  # Измените requests на orders