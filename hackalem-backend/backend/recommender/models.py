from datetime import date as calendar_date

from pydantic import BaseModel, ConfigDict, Field, field_validator
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

class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    city: str = Field(min_length=1, max_length=100)
    date: str
    event_format: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    budget: int = Field(gt=0, le=1_000_000_000, strict=True)

    duration: Optional[int] = Field(default=None, ge=1, le=24, strict=True)
    language: Optional[str] = Field(default=None, max_length=50)
    preferences: str = Field(default="", max_length=600)
    compare_date: Optional[str] = None

    @field_validator("preferences")
    @classmethod
    def clean_preferences(cls, value: str) -> str:
        return value.strip()

    @field_validator("city", "event_format", "category")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("поле не может быть пустым")
        return cleaned

    @field_validator("language")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("date", "compare_date")
    @classmethod
    def date_must_be_covered_by_dataset(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            parsed = calendar_date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("дата должна быть в формате YYYY-MM-DD") from exc

        start = calendar_date(2026, 9, 23)
        end = calendar_date(2026, 12, 31)
        if value != parsed.isoformat():
            raise ValueError("дата должна быть в формате YYYY-MM-DD")
        if not start <= parsed <= end:
            raise ValueError("дата должна быть в диапазоне 2026-09-23 — 2026-12-31")
        return value
