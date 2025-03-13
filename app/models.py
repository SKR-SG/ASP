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

class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False)  # Платформа ("TMS", "ATI" и т. д.)
    external_no = Column(String, unique=True, nullable=False)
    loading_city_id = Column(Integer, nullable=False)  # Город погрузки (ID)
    load_date = Column(DateTime, nullable=False)  # Дата погрузки
    unloading_city_id = Column(Integer, nullable=False)  # Город разгрузки (ID)
    unload_date = Column(DateTime, nullable=True)  # Дата разгрузки
    weight_volume = Column(String, nullable=True)  # Вес и объем в формате "20 т / 90 м³"
    vehicle_type = Column(String, nullable=True)  # Тип ТС
    loading_types = Column(String, nullable=True)  # Типы погрузки/разгрузки
    order_type = Column(String, nullable=False)  # 🔹 Тип заявки: "ASSIGNED", "AUCTION", "FREE"
    bid_price = Column(Float, nullable=True)  # 🔹 ставка завод либо последняя аукционная
    comment = Column(String, nullable=True)  # Комментарий к заявке
    cargo_name = Column(String, nullable=True)  # Наименование груза из правил распределения
    logistician_id = Column(Integer, nullable=False)  # ID логиста
    ati_price = Column(Float, nullable=True)  # Цена для АТИ
    is_published = Column(Boolean, default=False)  # Опубликована ли заявка


class Logist(Base):
    __tablename__ = "logists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)  # Имя логиста
    contact_id = Column(Integer, nullable=False)  # ID логиста в ATI

class DistributionRule(Base):
    __tablename__ = "distribution_rules"

    id = Column(Integer, primary_key=True)
    loading_city_id = Column(Integer, nullable=True)  # None = любой город
    unloading_city_id = Column(Integer, nullable=True)
    logist_id = Column(Integer, nullable=False)  # ID логиста
    margin_percent = Column(Float, nullable=True)  # Маржа в %
    auction_margin_percent = Column(Float, nullable=True)  # Маржа для аукциона
    cargo_name = Column(String, nullable=True)  # Название груза
    auto_publish = Column(Boolean, default=False)  # Авторазмещение
    publish_delay = Column(Integer, default=0)  # Задержка публикации

# Создание таблицы в БД
Base.metadata.create_all(engine)