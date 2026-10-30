import random

from shared.events import CounterEvent

from app.config import Settings
from app.services.publisher import EventBusUnavailable, EventPublisher


class LossyPublisher(EventPublisher):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.loss_rate = settings.chaos_ack_loss_rate

    async def publish(self, event: CounterEvent) -> None:
        await super().publish(event)
        if random.random() < self.loss_rate:
            raise EventBusUnavailable("simulated lost ack, retry later")
