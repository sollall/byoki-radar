from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class RawRecord(BaseModel):
    """Extract層の出力。Validation層に渡す前の共通スキーマ (spec section 4)。"""

    year: int
    week_number: int
    week_start_date: datetime
    prefecture: str
    region: str
    disease: str  # 自治体表記そのままの疾患名。Validation層でenumコードに正規化。
    patient_count: Optional[int] = None
    per_sentinel_count: Optional[float] = None
    source_tier: Literal["direct_parse", "llm_extract"]
    source_url: Optional[str] = None
    extracted_by: Literal["pandas", "llm"]


class ValidatedRecord(RawRecord):
    disease: str  # enumコード (masters.DISEASES のキー) に正規化済み
    validation_status: Literal["passed", "flagged"]
    flag_reason: Optional[str] = None
    fetched_at: datetime
