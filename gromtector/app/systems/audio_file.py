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


InputAudioDataEvent = namedtuple("InputAudioDataEvent", ["data", "rate"])


class AudioFileSystem(BaseSystem):
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
        self.audio_data_queue = queue.Queue()

        self.pa = pa.PyAudio()
        self.audio_out_stream = self.pa.open(
            format=self.pa.get_format_from_width(
                self.audio_file.audio_segment.seg.sample_width,  # or maybe frame_width?
            ),
            channels=self.audio_file.audio_segment.channels,
            rate=self.audio_file.audio_segment.frame_rate,
            output=True,
        )

        self.file_playback_done = False

    def shutdown(self):
        self.audio_out_stream.stop_stream()
        self.audio_out_stream.close()
        self.pa.terminate()

        self.running = False

    def update(self, elapsed_time_ms: int) -> None:
        if self.file_playback_done:
            return

        try:
            aud_f_data = self.audio_file.read()
            self.audio_out_stream.write(aud_f_data.data.tobytes())
            self.audio_data_queue.put(aud_f_data)
        except FilePlaybackFinished:
            self.file_playback_done = True

        dataset = []
        while not self.audio_data_queue.empty():
            dataset.append(self.audio_data_queue.get())
        if dataset:
            data = np.concatenate(dataset)
            self.get_event_manager().queue_event(
                "new_audio_data",
                InputAudioDataEvent(
                    data=data, rate=self.audio_file.audio_segment.frame_rate
                ),
            )
