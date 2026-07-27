from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, Dict, Any  # <-- ДОБАВИТЬ ЭТУ СТРОКУ
import config

Base = declarative_base()
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    subscription_active = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)
    tariff = Column(String, nullable=True)
    group_name = Column(String, default="users")
    sub_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    tariff = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(engine)


def get_user(telegram_id: int):
    session = SessionLocal()
    try:
        return session.query(User).filter_by(telegram_id=telegram_id).first()
    finally:
        session.close()


def create_user(telegram_id: int):
    session = SessionLocal()
    try:
        user = User(
            telegram_id=telegram_id,
            email=f"user_{telegram_id}",
            subscription_active=False,
            group_name="users"
        )
        session.add(user)
        session.commit()
        return user
    finally:
        session.close()


def update_user_subscription(telegram_id: int, tariff: str, days: int, group: str, sub_id: str = None):
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            from datetime import datetime, timedelta
            user.tariff = tariff
            user.group_name = group
            user.subscription_active = True
            user.subscription_end = datetime.now() + timedelta(days=days)
            if sub_id:
                user.sub_id = sub_id
            session.commit()
            return user
    finally:
        session.close()


def deactivate_subscription(telegram_id: int):
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.subscription_active = False
            user.group_name = "users"
            session.commit()
            return user
    finally:
        session.close()


def add_payment(telegram_id: int, tariff: str, amount: int):
    session = SessionLocal()
    try:
        payment = Payment(
            telegram_id=telegram_id,
            tariff=tariff,
            amount=amount,
            status="pending"
        )
        session.add(payment)
        session.commit()
        return payment
    finally:
        session.close()


def add_payment_and_get_id(telegram_id: int, tariff: str, amount: int) -> int:
    """Добавить платеж и вернуть его ID"""
    session = SessionLocal()
    try:
        payment = Payment(
            telegram_id=telegram_id,
            tariff=tariff,
            amount=amount,
            status="pending"
        )
        session.add(payment)
        session.commit()
        payment_id = payment.id
        return payment_id
    finally:
        session.close()


def update_payment_status(payment_id: int, status: str) -> Optional[Dict[str, Any]]:
    """
    Обновить статус платежа и вернуть данные в виде словаря

    Returns:
        Словарь с данными платежа или None
    """
    session = SessionLocal()
    try:
        payment = session.query(Payment).filter_by(id=payment_id).first()
        if payment:
            payment.status = status
            if status == "success":
                payment.completed_at = datetime.now()
            session.commit()

            # Возвращаем данные в виде словаря ДО закрытия сессии
            result = {
                "id": payment.id,
                "telegram_id": payment.telegram_id,
                "tariff": payment.tariff,
                "amount": payment.amount,
                "status": payment.status,
                "created_at": payment.created_at,
                "completed_at": payment.completed_at
            }
            return result
        return None
    finally:
        session.close()


def delete_user(telegram_id: int):
    """Удалить пользователя из БД"""
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            session.delete(user)
            session.commit()
            return True
        return False
    finally:
        session.close()


def get_payment_by_id(payment_id: int):
    """Получить платеж по ID"""
    session = SessionLocal()
    try:
        payment = session.query(Payment).filter_by(id=payment_id).first()
        if payment:
            session.expunge(payment)
            return payment
        return None
    finally:
        session.close()


def get_user_payments(telegram_id: int) -> list:
    """Получить все платежи пользователя"""
    session = SessionLocal()
    try:
        payments = session.query(Payment).filter_by(telegram_id=telegram_id).order_by(Payment.created_at.desc()).all()
        return payments
    finally:
        session.close()


def get_expiring_subscriptions(days_before: int = 3):
    """Получить пользователей, у которых подписка истекает через N дней"""
    session = SessionLocal()
    try:
        from datetime import datetime, timedelta
        start_date = datetime.now()
        end_date = datetime.now() + timedelta(days=days_before)

        users = session.query(User).filter(
            User.subscription_active == True,
            User.subscription_end >= start_date,
            User.subscription_end <= end_date
        ).all()
        return users
    finally:
        session.close()