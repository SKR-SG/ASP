import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, Date, DateTime, MetaData, JSON
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка подключения к БД
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ Ошибка: DATABASE_URL не задан! Проверь .env файл.")

metadata = MetaData()
Base = declarative_base(metadata=metadata)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    external_no = Column(String, unique=True, nullable=False)  # Внешний номер заявки
    loading_city = Column(String, nullable=False)  # Город загрузки (название)
    unloading_city = Column(String, nullable=False)  # Город выгрузки (название)
    load_date = Column(DateTime, nullable=False)  # Дата загрузки
    unload_date = Column(DateTime, nullable=True)  # Дата выгрузки
    weight_volume = Column(String, nullable=True)  # Вес и объем (в одном поле)
    vehicle_type = Column(String, nullable=True)  # Тип ТС
    loading_types = Column(String, nullable=True)  # Тип загрузки/разгрузки
    comment = Column(String, nullable=True)  # Комментарий
    cargo_name = Column(String, nullable=True)  # Наименование груза
    logistician_name = Column(String, nullable=True)  # Имя логиста
    ati_price = Column(Float, nullable=True)  # Цена для АТИ
    is_published = Column(String(50), nullable=True) # Опубликован ли груз на АТИ
    order_type = Column(String, nullable=False)  # Тип заявки (ASSIGNED, AUCTION, FREE)
    bid_price = Column(Float, nullable=True)  # Ставка (или последняя ставка для аукционов)
    platform = Column(String, nullable=False)  # Источник (TMS, API)
    loading_address = Column(String(255), nullable=True)  # ✅ поле для адреса погрузки
    unloading_address = Column(String(255), nullable=True)  # ✅ Поле для адреса выгрузки
    cargo_id = Column(String, nullable=True)  # 🆕 Сохраняем cargo_id для обновления/удаления

class Logist(Base):
    __tablename__ = "logists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)  # Имя логиста
    contact_id = Column(Integer, nullable=False)  # ID логиста в ATI

class DistributionRule(Base):
    __tablename__ = 'distribution_rules'

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False, index=True, default="transport2") # Площадка
    loading_city = Column(String, index=True)
    unloading_city = Column(String, index=True)
    logistician = Column(String) # Убедитесь, что атрибут logistician определен
    margin_percent = Column(Float, nullable=True) # Маржа в %
    auction_margin_percent = Column(Float, nullable=True) # Маржа для аукциона
    cargo_name = Column(String, nullable=True) # Название груза
    auto_publish = Column(Boolean, default=False) # Авторазмещение
    auto_publish_auction = Column(Boolean, default=False)       # авто-публикация для аукционных заявок
    publish_delay = Column(Integer, default=0) # Задержка публикации
    payment_days = Column(Integer, default=0) # Срок оплаты б/д

class Platform(Base):
    __tablename__ = 'platforms'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # имя площадки, например "transport2"
    enabled = Column(Boolean, default=True)  # включена или выключена площадка
    auth_data = Column(JSON, nullable=True)    # данные для авторизации (например, токены, URL и т.д.)
