from dataclasses import dataclass

from app.config import Settings
from app.services.counters import CountersService


@dataclass(frozen=True)
class Container:
    settings: Settings
    counters: CountersService
