""" Sensor model used by simultaneousOpened

    One entry in the ``sensors`` list of the app configuration.

    @Pythm / https://github.com/Pythm
"""
from __future__ import annotations

__version__ = "0.1.0"

from typing import Any, Mapping

from pydantic import BaseModel


class Sensor(BaseModel):
    sensor: str
    delay: int = 0

    @classmethod
    def from_yaml(cls, d: Mapping[str, Any]) -> 'Sensor':
        """ ``duration`` in the configuration is called ``delay`` in the model. Other keys are ignored. """
        d = dict(d)
        if 'duration' in d:
            d['delay'] = d.pop('duration')
        return cls(**d)
