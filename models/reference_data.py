from sqlalchemy import Column, String, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, BaseModel


class Specialization(Base, BaseModel):
    __tablename__ = "specializations"

    name = Column(String(100), unique=True, nullable=False, index=True)
    doctors = relationship("Doctor", back_populates="specialization")


class Department(Base, BaseModel):
    __tablename__ = "departments"

    name = Column(String(100), unique=True, nullable=False, index=True)
    doctors = relationship("Doctor", back_populates="department")


class SymptomCategory(Base, BaseModel):
    __tablename__ = "symptom_categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    symptoms = relationship("Symptom", back_populates="category")


class Symptom(Base, BaseModel):
    __tablename__ = "symptoms"

    name = Column(String(100), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    category_id = Column(ForeignKey('symptom_categories.id'), nullable=False, index=True)

    category = relationship("SymptomCategory", back_populates="symptoms")