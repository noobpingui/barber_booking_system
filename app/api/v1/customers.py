from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.customer import CustomerCreate, CustomerRead
from app.services import customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    existing = customer_service.get_customer_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this email already exists.",
        )
    return customer_service.create_customer(db, data)


@router.get("/", response_model=list[CustomerRead])
def list_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return customer_service.get_all_customers(db, skip=skip, limit=limit)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = customer_service.get_customer_by_id(db, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return customer
