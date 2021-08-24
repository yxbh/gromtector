
from collections import defaultdict


from collections import defaultdict
import queue


class EventManager:
    def __init__(self):
        self.listeners = defaultdict(lambda: [])
        self.event_queue = queue.Queue()

    def add_listener(self, event_type, listener) -> None:
        self.listeners[event_type].append(listener)

    def remove_listener(self, event_type, listener):
        # self.listeners[event_type] = [
        #     l for l in self.listeners[event_type] if l != listener
        # ]
        self.listeners[event_type].remove(listener)

    def queue_event(self, event_type, event) -> None:
        self.event_queue.put((event_type, event))

    def dispatch_event(self, event_type, event) -> None:
        for listener in self.listeners[event_type]:
            listener(event_type, event)

    def dispatch_queued_events(self) -> None:
        while not self.event_queue.empty():
            event_type, event = self.event_queue.get()
            self.dispatch_event(event_type=event_type, event=event)

    def shutdown(self) -> None:
        self.listeners.clear()

