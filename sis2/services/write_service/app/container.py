from dataclasses import dataclass

from app.config import Settings
from app.services.dedup import ViewDedup
from app.services.publisher import EventPublisher
from app.services.view_token import ViewTokens


@dataclass(frozen=True)
class Container:
    settings: Settings
    publisher: EventPublisher
    dedup: ViewDedup
    view_tokens: ViewTokens
