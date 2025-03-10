from fastapi import FastAPI
from app.routes import users, requests

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(requests.router, prefix="/requests", tags=["Requests"])