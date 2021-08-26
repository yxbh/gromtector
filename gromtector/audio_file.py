import os

import pyaudio
import numpy as np
import audiosegment as ad


DEFAULT_CHUNK_SIZE = 8192  # number of samples to take per read
DEFAULT_CHUNK_SIZE = 1024


class FilePlaybackFinished(Exception):
    pass


class AudioFile:
    def __init__(self, file_path, chunk_size=None):
        self.file_path = os.path.abspath(file_path)
        if not os.path.exists(self.file_path):
            raise FileNotFoundError('"{}" not found.'.format(self.file_path))
        self.audio_segment = ad.from_file(self.file_path)
        if self.audio_segment.seg.channels > 1:
            self.audio_segment = self.audio_segment.resample(
                channels=1,
                sample_rate_Hz=self.audio_segment.seg.frame_rate,
                sample_width=self.audio_segment.seg.sample_width,
            )
        self.cursor = 0
        self.chunk_size = chunk_size if chunk_size else DEFAULT_CHUNK_SIZE

    def open(self):
        self.cursor = 0

    def read(self):
        end = self.cursor + self.chunk_size
        seg_raw_data = self.audio_segment.seg.raw_data
        if end >= len(seg_raw_data):
            raise FilePlaybackFinished("All over")

        if end > len(seg_raw_data):
            end = len(seg_raw_data)
        raw_data = seg_raw_data[self.cursor : end]
        self.cursor = end
        return np.frombuffer(raw_data, dtype=np.int16)

    def close(self):
        self.cursor = 0

    @property
    def sample_rate(self):
        return self.audio_segment.frame_rate

    @property
    def desireable_sample_interval_ms(self):
        sample_per_ms = self.sample_rate / 1000  # sample per ms
        sample_length = int(
            self.chunk_size / self.audio_segment.seg.frame_width / sample_per_ms
        )  # chunk duration.
        return sample_length
