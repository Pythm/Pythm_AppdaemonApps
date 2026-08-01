from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional, Union
from pydantic import BaseModel

class Sensor(BaseModel):
    sensor: str
    delay: int = 0
    constraints: Optional[str] = None
    handler: Any | None = None
    last_state: bool | None = None
    @classmethod
    def from_yaml(cls, d: Mapping[str, Any]) -> 'Sensor':
        d = dict(d)
        if 'duration' in d:
            d['delay'] = d.pop('duration')
        return cls(**d)
