# schemas/ingredient.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class IngredientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, description="Unique ingredient name, e.g., 'olive oil'")
    category: Optional[str] = Field(
        None,
        max_length=80,
        description="Optional category, e.g., 'produce', 'dairy', 'spices'"
    )
    # Unit normalization fields
    canonical_unit_type: Optional[Literal["weight", "volume", "count"]] = Field(
        None,
        description="Type of canonical unit: weight, volume, or count"
    )
    canonical_unit: Optional[str] = Field(
        None,
        max_length=16,
        description="Canonical unit code: g, ml, count, etc."
    )
    avg_weight_per_unit_g: Optional[float] = Field(
        None,
        ge=0,
        description="Average weight in grams for one unit (e.g., one egg = 50g)"
    )
    density_g_per_ml: Optional[float] = Field(
        None,
        ge=0,
        description="Density in grams per milliliter for volume-to-weight conversion"
    )
    pieces_per_package: Optional[int] = Field(
        None,
        ge=1,
        description="Number of pieces in a standard package"
    )


class IngredientUpdate(BaseModel):
    # For PATCH/PUT if you allow editing later
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    category: Optional[str] = Field(None, max_length=80)
    # Unit normalization fields
    canonical_unit_type: Optional[Literal["weight", "volume", "count"]] = Field(
        None,
        description="Type of canonical unit: weight, volume, or count"
    )
    canonical_unit: Optional[str] = Field(
        None,
        max_length=16,
        description="Canonical unit code: g, ml, count, etc."
    )
    avg_weight_per_unit_g: Optional[float] = Field(
        None,
        ge=0,
        description="Average weight in grams for one unit"
    )
    density_g_per_ml: Optional[float] = Field(
        None,
        ge=0,
        description="Density in grams per milliliter"
    )
    pieces_per_package: Optional[int] = Field(
        None,
        ge=1,
        description="Number of pieces in a standard package"
    )


class IngredientOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    category: Optional[str] = None
    created_at: datetime
    # Unit normalization fields
    canonical_unit_type: Optional[str] = None
    canonical_unit: Optional[str] = None
    avg_weight_per_unit_g: Optional[float] = None
    density_g_per_ml: Optional[float] = None
    pieces_per_package: Optional[int] = None
