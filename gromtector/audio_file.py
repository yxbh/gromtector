import pyaudio
import numpy as np
import audiosegment as ad


DEFAULT_CHUNK_SIZE = 8192  # number of samples to take per read


class AudioFile:
    def __init__(self, file_path, chunk_size=None):
        self.audio_segment = ad.from_file(file_path)
        self.audio_segment = self.audio_segment.resample(channels=1)
        self.cursor = 0
        self.chunk_size = chunk_size if chunk_size else DEFAULT_CHUNK_SIZE

    def open(self):
        self.cursor = 0

    def read(self):
        end = self.cursor + self.chunk_size
        seg_raw_data = self.audio_segment.seg.raw_data
        if end >= len(seg_raw_data):
            raise RuntimeError("All over")
        
        if end > len(seg_raw_data):
            end = len(seg_raw_data)
        raw_data = seg_raw_data[self.cursor: end]
        self.cursor = end
        return np.array(raw_data)

    def close(self):
        self.cursor = 0

    @property
    def sample_rate(self):
        return self.audio_segment.frame_rate
