# point.py
from dataclasses import dataclass

@dataclass
class Point:
    id: int
    lat: float
    lon: float

    def to_tuple(self):
        return (self.lat, self.lon)
