from pydantic import BaseModel
from typing import Optional


class Contractor(BaseModel):
    id: str
    anon_name: str

    categories: list[str]
    city: str

    city_imputed: bool
    synthetic: bool

    price_from_kzt: int
    price_imputed: bool

    event_formats: list[str]
    languages: list[str]

    max_hours: Optional[int] = None

    busy_dates: list[str]

    description: str