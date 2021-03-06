from typing import Mapping

from ..EventManager import EventManager
from ..BaseApplication import BaseApplication

class BaseSystem:
    def __init__(self, app: BaseApplication, config: dict=None):
        if not app:
            raise RuntimeError("Where mah app?!")
        self.app = app
        self.config = config

    def get_app(self) -> BaseApplication:
        return self.app

    def get_event_manager(self) -> EventManager:
        return self.get_app().get_event_manager()

    def get_config(self) -> Mapping:
        return self.config

    def init(self,) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def update(self, elapsed_time: int) -> None:
        pass

    def run(self) -> None:
        pass