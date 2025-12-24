"""
Municipality models for IBGE data.
"""

from pydantic import BaseModel, Field
from typing import List


class Municipality(BaseModel):
    """Brazilian municipality data from IBGE."""

    id: int = Field(..., description="IBGE municipality code")
    nome: str = Field(..., description="Municipality name")
    uf: str = Field(..., description="State abbreviation (e.g., SP)")

    class Config:
        json_schema_extra = {
            "example": {"id": 3550308, "nome": "São Paulo", "uf": "SP"}
        }


class MunicipalityListResponse(BaseModel):
    """Response containing list of municipalities."""

    municipalities: List[Municipality]
    total: int = Field(..., description="Total number of municipalities")
