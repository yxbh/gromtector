import logging

import pygame as pg

from .BaseSystem import BaseSystem

logger = logging.getLogger(__name__)


class KeyboardSystem(BaseSystem):
    def init(self):
        self.get_event_manager().add_listener("keyboard_event", self.handle_kb_evt)

        self.running = True

    def handle_kb_evt(self, event_type, kb_event):
        logger.debug("%s, %s", event_type, kb_event)
        evt_manager = self.get_event_manager()
        if kb_event.key == pg.K_SPACE:
            if self.app.is_server:
                evt_manager.queue_event("broadcast_to_clients", {
                    "event_type": "test"
                })
            if self.app.is_client:
                evt_manager.queue_event("push_to_server", {
                    "event_type": "test"
                })

    def shutdown(self):
        self.running = False

    def update(self, elapsed_time_ms: int) -> None:
        pass

    def run(self):
        pass
