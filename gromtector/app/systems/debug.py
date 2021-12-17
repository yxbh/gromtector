import logging

from .BaseSystem import BaseSystem

logger = logging.getLogger(__name__)


class DebugSystem(BaseSystem):
    def init(self):
        if self.app.is_server:
            self.get_event_manager().add_listener("push_to_server", self.test)
            self.get_event_manager().add_listener("test", self.test)
        else:
            self.get_event_manager().add_listener("broadcast_to_clients", self.test)
        self.get_event_manager().add_listener("new_audio_data", self.test)

    def test(self, event_type, audio_mic_evt):
        # logger.debug("Received {} len of audio data.".format(len(audio_mic_evt.data)))
        if event_type in ["test", "push_to_server", "broadcast_to_clients"]:
            logger.debug("Received test event.")
        pass

    def update(self, elapsed_time_ms: int) -> None:
        # logger.debug("{}ms elapsed.".format(elapsed_time_ms))
        pass

    def shutdown(self):
        self.get_event_manager().remove_listener("new_audio_data", self.test)
