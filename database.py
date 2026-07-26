from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

Base = declarative_base()
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)  # user_{telegram_id}
    subscription_active = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)
    tariff = Column(String, nullable=True)  # trial, monthly, quarterly
    group_name = Column(String, default="users")  # текущая группа в панели
    sub_id = Column(String, nullable=True)  # subId из панели
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    tariff = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending, success, failed
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


def update_payment_status(payment_id: int, status: str):
    session = SessionLocal()
    try:
        payment = session.query(Payment).filter_by(id=payment_id).first()
        if payment:
            payment.status = status
            if status == "success":
                payment.completed_at = datetime.now()
            session.commit()
            return payment
    finally:
        session.close()