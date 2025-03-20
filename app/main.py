import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import users, orders, distribution_rules, platforms, logists

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # или можно использовать ["*"] для разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(distribution_rules.router, prefix="/distribution-rules", tags=["distribution_rules"])
app.include_router(platforms.router, prefix="/platforms", tags=["Platforms"])
app.include_router(logists.router, prefix="/logists", tags=["logists"])

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)