import logging

from .BaseSystem import BaseSystem

logger = logging.getLogger(__name__)


class DebugSystem(BaseSystem):
    def init(self):
        self.get_event_manager().add_listener("new_audio_mic_data", self.test)

    def test(self, event_type, audio_mic_evt):
        logger.debug("Received {} len of audio data.".format(len(audio_mic_evt.data)))

    def update(self, elapsed_time_ms: int) -> None:
        # logger.debug("{}ms elapsed.".format(elapsed_time_ms))
        pass
