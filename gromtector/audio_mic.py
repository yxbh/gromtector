from contextlib import contextmanager

import pyaudio
import numpy as np

from gromtector.logging import logger

DEFAULT_FORMAT = pyaudio.paInt16  # conversion format for PyAudio stream
DEFAULT_CHANNELS = 1  # microphone audio channels
DEFAULT_SAMPLE_RATE = 48_000  # num audio sample per sec
DEFAULT_SAMPLE_RATE = 44_100
DEFAULT_CHUNK_SIZE = 8192  # number of samples to take per read

# SAMPLE_LENGTH = int(CHUNK_SIZE * 1_000 / SAMPLE_RATE)  # length of each sample in ms
DEFAULT_SAMPLE_PER_MS = DEFAULT_SAMPLE_RATE / 1000  # sample per ms
DEFAULT_SAMPLE_LENGTH = int(
    DEFAULT_CHUNK_SIZE / DEFAULT_SAMPLE_PER_MS
)  # chunk duration.


def _open_mic(sample_rate, channels, chunk_size, format):
    """
    open_mic:
    creates a PyAudio object and initializes the mic stream
    inputs: none
    ouputs: stream, PyAudio object
    """

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=format,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_size,
    )
    return stream, pa


def get_data(stream: pyaudio.Stream, chunk_size: int) -> np.ndarray:
    """
    get_data:
    reads from the audio stream for a constant length of time, converts it to data
    inputs: stream, PyAudio object
    outputs: int16 data array
    """

    input_data = stream.read(chunk_size, exception_on_overflow=False)
    data = np.frombuffer(input_data, np.int16)
    return data


def get_sample(stream: pyaudio.Stream, chunk_size: int) -> np.ndarray:
    """
    get_sample:
    gets the audio data from the microphone
    inputs: audio stream and PyAudio object
    outputs: int16 array"""

    data = get_data(stream, chunk_size)
    return data


class AudioMic:
    def __init__(self, open=False, sample_rate=None, channels=None, chunk_size=None):
        self.sample_rate = sample_rate if sample_rate else DEFAULT_SAMPLE_RATE
        self.channels = channels if channels else DEFAULT_CHANNELS
        self.chunk_size = chunk_size if chunk_size else DEFAULT_CHUNK_SIZE
        self.format = DEFAULT_FORMAT
        self.stream = None
        self.pa = None
        if open:
            self.open()

    def open(self):
        if self.stream is not None or self.pa is not None:
            raise RuntimeError("Opening an open mic.")
        stream, pa = _open_mic(
            sample_rate=self.sample_rate,
            channels=self.channels,
            chunk_size=self.chunk_size,
            format=self.format,
        )
        self.stream = stream
        self.pa = pa

    def read(self):
        return get_sample(self.stream, self.chunk_size)

    def get_desireable_sample_length(self):
        sample_per_ms = self.sample_rate / 1000  # sample per ms
        sample_length = int(self.chunk_size / sample_per_ms)  # chunk duration.
        return sample_length

    @property
    def desireable_sample_length(self):
        return self.get_desireable_sample_length()

    def close(self):
        if not self.stream:
            raise RuntimeError("Closing an unopen mic.")
        if not self.pa:
            raise RuntimeError("Closing an unopen mic.")
        self.stream.stop_stream()
        self.stream.close()
        self.stream = None
        self.pa.terminate()
        self.pa = None


@contextmanager
def open_mic():
    try:
        mic = AudioMic()
        mic.open()
        yield mic
    finally:
        mic.close()
