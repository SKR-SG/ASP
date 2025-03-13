import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка подключения к БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:159753@localhost/acp_db")
Base = declarative_base()
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
    external_no = Column(String, unique=True, nullable=False)
    loading_city_id = Column(Integer, nullable=False)
    unloading_city_id = Column(Integer, nullable=False)
    load_date = Column(DateTime, nullable=False)
    unload_date = Column(DateTime, nullable=True)
    weight = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    logistician = Column(Integer, nullable=False)  # ID логиста
    ati_price = Column(Float, nullable=True)  # Цена для АТИ
    is_published = Column(Boolean, default=False)
    is_auction = Column(Boolean, default=False)  # Флаг аукциона
    owner_id = Column(Integer, ForeignKey("users.id"))  # Владелец заявки
    owner = relationship("User")  # Связь с пользователем

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