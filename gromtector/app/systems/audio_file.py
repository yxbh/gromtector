from datetime import datetime
import logging
import threading
import os
import platform
import queue
from collections import namedtuple
import numpy as np
import pyaudio as pa

from gromtector.audio_file import AudioFile, FilePlaybackFinished
from .BaseSystem import BaseSystem

logger = logging.getLogger(__name__)


InputAudioDataEvent = namedtuple(
    "InputAudioDataEvent", ["data", "rate", "begin_timestamp"]
)


class AudioFileSystem(BaseSystem):
    pa = None
    audio_out_stream = None
    audio_file: AudioFile = None
    file_playback_done: bool = True
    read_write_thread: threading.Thread = None
    audio_data_queue: queue.Queue = queue.Queue()
    running: bool = False

    def init(self):
        input_file_path = self.config.get("--file", None)
        if not input_file_path:
            raise RuntimeError(
                'Cannot load audio file as the "--file" option was not provided.'
            )
        if platform.system() == "Darwin" and input_file_path.startswith("~"):
            input_file_path = os.path.expanduser(input_file_path)
        input_file_path = os.path.abspath(input_file_path)
        if not os.path.exists(input_file_path):
            raise RuntimeError('Cannot locate audio file "{}"'.format(input_file_path))

        self.audio_file = AudioFile(file_path=self.config["--file"])

        self.pa = pa.PyAudio()
        self.audio_out_stream = self.pa.open(
            format=self.pa.get_format_from_width(
                self.audio_file.audio_segment.seg.sample_width,  # or maybe frame_width?
            ),
            channels=self.audio_file.audio_segment.channels,
            rate=self.audio_file.audio_segment.frame_rate,
            output=True,
        )

        self.running = True
        self.file_playback_done = False

    def shutdown(self) -> None:
        self.audio_out_stream.stop_stream()
        self.audio_out_stream.close()
        self.pa.terminate()

        self.running = False

    def run(self) -> None:
        self.read_write_thread = threading.Thread(
            target=self.__class__.run_read_write_thread, args=(self,)
        )
        self.read_write_thread.start()

    def update(self, elapsed_time_ms: int) -> None:
        if self.file_playback_done:
            return

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
                    rate=self.audio_file.audio_segment.frame_rate,
                    begin_timestamp=dataset_utcbegin,
                ),
            )

    @classmethod
    def run_read_write_thread(cls, system) -> None:
        while system.running:
            if system.file_playback_done:
                break

            try:
                utcnow = datetime.utcnow()
                aud_f_data = system.audio_file.read()
                system.audio_out_stream.write(aud_f_data.data.tobytes())
                system.audio_data_queue.put((aud_f_data, utcnow))
            except FilePlaybackFinished:
                system.file_playback_done = True
