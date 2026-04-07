
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Создание движка с оптимизациями под SQLite (если используется)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,  # Включить для отладки SQL-запросов
    pool_pre_ping=True,  # Проверка соединения перед использованием
)

_base = None

def get_base():
    global _base
    if _base is None:
        _base = declarative_base()
    return _base

Base = get_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DatabaseManager:
    """Менеджер базы данных с улучшенной обработкой ошибок и логированием."""

    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.Base = get_base()  # Используем функцию для получения базы

    def create_tables(self) -> None:
        """Создаёт все таблицы, если они ещё не существуют."""
        try:
            self.Base.metadata.create_all(bind=self.engine)
            logger.info("Таблицы базы данных успешно созданы или уже существуют.")
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            raise

    def get_db(self) -> Generator[Session, None, None]:
        """Генератор сессии базы данных для использования в FastAPI."""
        db = self.SessionLocal()
        try:
            yield db
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка в транзакции БД: {e}")
            raise
        finally:
            db.close()


db_manager = DatabaseManager()


# Зависимость для внедрения сессии БД
def get_db() -> Generator[Session, None, None]:
    """Зависимость FastAPI для получения сессии базы данных."""
    yield from db_manager.get_db()


# Отложенная загрузка моделей — чтобы Base была доступна
# init_models() больше не нужна, так как модели инициализируются через get_base() при определении классов.