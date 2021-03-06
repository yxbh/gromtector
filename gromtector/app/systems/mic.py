from datetime import datetime, timezone
import logging
import threading
import queue
from collections import namedtuple
import numpy as np

from .BaseSystem import BaseSystem

from gromtector.audio_mic import AudioMic, CallbackAudioMic

logger = logging.getLogger(__name__)


InputAudioDataEvent = namedtuple(
    "InputAudioDataEvent", ["data", "rate", "begin_timestamp"]
)


class AudioMicSystem(BaseSystem):
    def init(self):
        self.mic = AudioMic(channels=1, sample_rate=44100)
        self.mic.open()
        self.running = True
        self.audio_thread = None
        self.audio_data_queue = queue.Queue()

    def shutdown(self):
        self.running = False
        self.audio_thread.join()
        self.mic.close()

    def update(self, elapsed_time_ms: int) -> None:
        dataset = []
        dataset_utcbegin = None
        while not self.audio_data_queue.empty():
            audio_raw, utc_begin = self.audio_data_queue.get()
            if not dataset_utcbegin:
                dataset_utcbegin = utc_begin
            dataset.append(audio_raw)
        if dataset:
            data = np.concatenate(dataset)
            self.get_event_manager().queue_event(
                "new_audio_data",
                InputAudioDataEvent(
                    data=data,
                    rate=self.mic.sample_rate,
                    begin_timestamp=dataset_utcbegin,
                ),
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
            if hasattr(system.mic, "buffer") and not system.mic.buffer:
                continue

            utcnow = datetime.now(tz=timezone.utc)
            data = system.mic.read()
            if data.size:
                system.audio_data_queue.put((data, utcnow))

            # logger.debug("Just read {} bytes of audio data.".format(len(data)))

        logger.debug("Reaching the end of the audio mic thread.")
