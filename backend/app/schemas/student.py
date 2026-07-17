from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date
import uuid

class StudentBase(BaseModel):
    first_name: str
    last_name: str
    admission_number: str
    date_of_birth: Optional[date] = None

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)
