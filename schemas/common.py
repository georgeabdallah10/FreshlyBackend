# schemas/common.py
from pydantic import BaseModel

class ErrorOut(BaseModel):
    detail: str