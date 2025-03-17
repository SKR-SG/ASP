import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, Date, DateTime, MetaData
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка подключения к БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:159753@localhost/acp_db")
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
    is_published = Column(Boolean, default=False)  # Опубликован ли груз на АТИ
    order_type = Column(String, nullable=False)  # Тип заявки (ASSIGNED, AUCTION, FREE)
    bid_price = Column(Float, nullable=True)  # Ставка (или последняя ставка для аукционов)
    platform = Column(String, nullable=False)  # Источник (TMS, API)
    address = Column(String, nullable=True)  # 🆕 поле для извлеченного адреса выгрузки

class Logist(Base):
    __tablename__ = "logists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)  # Имя логиста
    contact_id = Column(Integer, nullable=False)  # ID логиста в ATI

class DistributionRule(Base):
    __tablename__ = 'distribution_rules'

    id = Column(Integer, primary_key=True, index=True)
    loading_city = Column(String, index=True)
    unloading_city = Column(String, index=True)
    logistician = Column(String) # Убедитесь, что атрибут logistician определен
    margin_percent = Column(Float, nullable=True) # Маржа в %
    auction_margin_percent = Column(Float, nullable=True) # Маржа для аукциона
    cargo_name = Column(String, nullable=True) # Название груза
    auto_publish = Column(Boolean, default=False) # Авторазмещение
    publish_delay = Column(Integer, default=0) # Задержка публикации
    payment_days = Column(Integer, default=0) # Срок оплаты б/д


# Создание таблицы в БД
Base.metadata.create_all(engine)