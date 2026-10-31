"""Scene description, not a menu of preset buildings."""
from typing import Literal
import re
from pydantic import BaseModel, ConfigDict, model_validator, Field

class Data(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)

    @model_validator(mode='before')
    @classmethod
    def normalize_numeric_strings(cls, data):
        # Normalize only declared float fields. Never coerce IDs, booleans or units.
        if not isinstance(data, dict):
            return data
        result = dict(data)
        for name, field in cls.model_fields.items():
            value = result.get(name)
            if field.annotation is float and isinstance(value, str):
                text = value.strip()
                if len(text) <= 64 and re.fullmatch('[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?', text):
                    result[name] = float(text)
        return result

class Color(Data):
    r: float
    g: float
    b: float

class Room(Data):
    id: str
    name: str
    x: float
    y: float
    width: float
    depth: float
    height: float
    floor_color: Color
    kind: str | None = Field(default=None,max_length=32)

class Opening(Data):
    id: str
    kind: Literal['door', 'window', 'portal']
    axis: Literal['x', 'y']
    x: float
    y: float
    width: float
    bottom: float
    height: float
    entrance: bool

class Furniture(Data):
    id: str
    room_id: str
    kind: Literal['bed', 'sofa', 'table', 'chair', 'kitchen', 'wardrobe', 'toilet', 'basin', 'shower', 'plant', 'box', 'cylinder', 'treadmill', 'exercise_bike', 'weight_rack', 'bench', 'car']
    x: float
    y: float
    width: float
    depth: float
    height: float
    rotation_deg: float
    color: Color

class FloorLayout(Data):
    level: int = Field(ge=1)
    elevation: float
    name: str
    rooms: list[Room]
    openings: list[Opening]
    furniture: list[Furniture]
    access_roots: list[str] = Field(default_factory=lambda: ['vertical_core'])

class VerticalCore(Data):
    x: float
    y: float
    width: float
    depth: float
    storey_height: float
    lift: bool = False

class SiteRect(Data):
    x: float
    y: float
    width: float
    depth: float

class ParkingBay(SiteRect):
    id: str

class SitePlan(SiteRect):
    parking: list[ParkingBay] = Field(default_factory=list)
    aisles: list[SiteRect] = Field(default_factory=list)
    park: SiteRect | None = None
    pool: SiteRect | None = None

class Scene(Data):
    width: float
    depth: float
    wall_color: Color
    accent_color: Color
    roof_color: Color
    rooms: list[Room]
    openings: list[Opening]
    furniture: list[Furniture]
    shape: Literal['rectangle', 'L', 'U'] | None = None
    courtyard_corner: Literal['rear-right', 'rear-left'] | None = None
    layout_variant: int = Field(default=0, ge=0, le=9999)
    storeys: int = Field(default=1, ge=1)
    storey_height: float = 3.45
    upper_floors: list[FloorLayout] = Field(default_factory=list)
    vertical_core: VerticalCore | None = None
    site: SitePlan | None = None
    access_roots: list[str] = Field(default_factory=list)

class Response(Data):
    message: str
    ready: bool
    assumptions: list[str]
    unsupported: list[str]
    scene: Scene | None
