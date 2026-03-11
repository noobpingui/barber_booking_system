from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate


def get_customer_by_email(db: Session, email: str) -> Customer | None:
    return db.query(Customer).filter(Customer.email == email).first()


def get_customer_by_id(db: Session, customer_id: int) -> Customer | None:
    return db.query(Customer).filter(Customer.id == customer_id).first()


def get_all_customers(db: Session, skip: int = 0, limit: int = 100) -> list[Customer]:
    return db.query(Customer).order_by(Customer.full_name).offset(skip).limit(limit).all()


def get_or_create_customer(db: Session, data: CustomerCreate) -> Customer:
    """Return the existing customer with this email, or create a new one."""
    existing = get_customer_by_email(db, data.email)
    return existing if existing else create_customer(db, data)


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    customer = Customer(
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
