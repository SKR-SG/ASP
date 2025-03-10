from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)  # Вн. номер
    platform = Column(String, nullable=False)  # Площадка
    load_date = Column(Date, nullable=False)  # Дата погрузки
    origin = Column(String, nullable=False)  # Загрузка (город)
    unload_date = Column(Date, nullable=False)  # Дата разгрузки
    destination = Column(String, nullable=False)  # Выгрузка (город)
    rate_factory = Column(Float, nullable=True)  # Ставка завода
    rate_auction = Column(Float, nullable=True)  # Ставка аукциона
    cargo_type = Column(String, nullable=False)  # Тип груза
    weight_volume = Column(String, nullable=False)  # Вес / Объём
    vehicle_type = Column(String, nullable=False)  # Тип ТС
    load_unload_type = Column(String, nullable=False)  # Тип погр/разгр
    logistician = Column(String, nullable=False)  # Логист (ФИО)
    ati_price = Column(Float, nullable=True)  # Цена АТИ
    is_published = Column(Boolean, default=False)  # Опубликована
    owner_id = Column(Integer, ForeignKey("users.id"))  # Владелец заявки
    owner = relationship("User")  # Связь с пользователем