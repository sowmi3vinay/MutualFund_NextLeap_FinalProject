from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.review_intelligence import generate_review_intelligence

router = APIRouter()


class PulseRequest(BaseModel):
    reviews_csv_path: Optional[str] = "data/reviews/sample_reviews.csv"
    week_start: Optional[str] = None
    week_end: Optional[str] = None


@router.post("/generate")
def generate_pulse(request: PulseRequest):
    return generate_review_intelligence(request.reviews_csv_path)
