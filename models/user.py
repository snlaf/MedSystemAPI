from sqlalchemy import Column, String, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
from .enums import RoleEnum


class User(Base, BaseModel):
    __tablename__ = "users"

    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(RoleEnum), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    patient_id = Column(ForeignKey('patients.id'), unique=True, nullable=True)
    doctor_id = Column(ForeignKey('doctors.id'), unique=True, nullable=True)

    patient = relationship("Patient", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)