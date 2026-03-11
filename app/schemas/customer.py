from pydantic import BaseModel, EmailStr, Field, field_validator


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name(cls, v: str) -> str:
        # Ensures "  Bob  " is stored as "Bob" and "   " fails min_length=1.
        return v.strip() if isinstance(v, str) else v

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        # Normalize to lowercase so "John@EXAMPLE.COM" and "john@example.com"
        # are treated as the same address consistently across all operations.
        return v.strip().lower() if isinstance(v, str) else v


class CustomerRead(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str

    model_config = {"from_attributes": True}
