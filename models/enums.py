from enum import Enum

class GenderEnum(str, Enum):
    male = 'м'
    female = 'ж'

class StatusEnum(str, Enum):
    active = 'активно'
    completed = 'завершено'
    cancelled = 'отменено'

class RoleEnum(str, Enum):
    patient = 'patient'
    doctor = 'doctor'
    admin = 'admin'