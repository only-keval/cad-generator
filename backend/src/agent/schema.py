from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional


class Primitive(BaseModel):
    id: str
    type: Literal["box", "cylinder", "sphere", "cone"]
    dimensions: dict
    position: List[float]
    orientation: Literal["X", "Y", "Z"]

    @field_validator("position")
    def validate_position(cls, v):
        if len(v) != 3:
            raise ValueError("position must have 3 values")
        return v


class Constraint(BaseModel):
    type: Literal["center", "stack", "offset"]
    target: str
    reference: Optional[str] = None
    axis: Optional[Literal["X", "Y", "Z"]] = None
    value: Optional[float] = None
    axes: Optional[List[Literal["X", "Y", "Z"]]] = None

    @field_validator("axes")
    def validate_axes(cls, v, info):
        if info.data.get("type") == "center" and not v:
            raise ValueError("center requires axes")
        return v

    @field_validator("value")
    def validate_value(cls, v, info):
        if info.data.get("type") == "offset" and v is None:
            raise ValueError("offset requires value")
        return v


class StructuredPlan(BaseModel):
    primitives: List[Primitive]
    constraints: List[Constraint]

    @field_validator("primitives")
    def validate_primitives(cls, v):
        if not v:
            raise ValueError("must have at least one primitive")
        if v[0].position != [0, 0, 0]:
            raise ValueError("first primitive must be at origin")
        return v