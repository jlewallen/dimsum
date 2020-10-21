from typing import Union, Any


class EventBus:
    async def publish(self, event: Union[Any]):
        raise NotImplementedError
