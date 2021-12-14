from .EventManager import EventManager

class BaseApplication:
    def get_event_manager(self) -> EventManager:
        return None

    @property
    def is_server(self) -> bool:
        return False

    @property
    def is_client(self) -> bool:
        return False
