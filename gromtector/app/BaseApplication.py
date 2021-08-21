from .event_manager import EventManager

class BaseApplication:
    def get_event_manager(self) -> EventManager:
        return None
