import logging
import threading
import queue
from collections import namedtuple
import numpy as np

from .BaseSystem import BaseSystem

from gromtector.audio_mic import AudioMic, CallbackAudioMic

logger = logging.getLogger(__name__)


InputAudioMicEvent = namedtuple("InputAudioMicEvent", ["data", "rate"])


class AudioMicSystem(BaseSystem):
    def init(self):
        self.mic = CallbackAudioMic()
        self.mic.open()
        self.running = True
        self.audio_thread = None
        self.audio_data_queue = queue.Queue()

    def shutdown(self):
        self.running = False
        self.audio_thread.join()
        self.mic.close()

    def update(self, elapsed_time_ms: int) -> None:
        # logger.debug(self.__class__)
        dataset = []
        while not self.audio_data_queue.empty():
            dataset.append(self.audio_data_queue.get())
        if dataset:
            data = np.concatenate(dataset) 
            self.get_event_manager().queue_event(
                "new_audio_mic_data",
                InputAudioMicEvent(data=data, rate=self.mic.sample_rate),
            )
        pass

    def run(self):
        self.audio_thread = threading.Thread(
            target=self.__class__.run_audio_mic_thread, args=(self,)
        )
        self.audio_thread.start()

    @classmethod
    def run_audio_mic_thread(cls, system):
        while system.running:
            if not system.mic.stream.is_active():
                logger.info("Audio mic is no longer active.")
                break
            if system.mic.stream.is_stopped():
                logger.info("Audio mic stream has stopped.")
                break
            if not system.mic.buffer:
                continue

            data = system.mic.read()
            if data.size:
                system.audio_data_queue.put(data)

            # logger.debug("Just read {} bytes of audio data.".format(len(data)))

        logger.debug("Reaching the end of the audio mic thread.")
