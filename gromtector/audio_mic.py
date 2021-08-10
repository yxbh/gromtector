from contextlib import contextmanager

import pyaudio
import numpy as np

from gromtector.logging import logger

FORMAT = pyaudio.paInt16  # conversion format for PyAudio stream
CHANNELS = 2  # microphone audio channels
SAMPLE_RATE = 16_000  # num audio sample per sec
# SAMPLE_RATE = 8_000
SAMPLE_RATE = 44_100
SAMPLE_RATE = 48_000
CHUNK_SIZE = 8192  # number of samples to take per read
# CHUNK_SIZE = 8_256
# CHUNK_SIZE = 16_512
# SAMPLE_LENGTH = int(CHUNK_SIZE * 1_000 / SAMPLE_RATE)  # length of each sample in ms
SAMPLE_PER_MS = SAMPLE_RATE / 1000  # sample per ms
SAMPLE_LENGTH = int(CHUNK_SIZE / SAMPLE_PER_MS)  # chunk duration.


def _open_mic():
    """
    open_mic:
    creates a PyAudio object and initializes the mic stream
    inputs: none
    ouputs: stream, PyAudio object
    """

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )
    return stream, pa


def get_data(stream: pyaudio.Stream) -> np.ndarray:
    """
    get_data:
    reads from the audio stream for a constant length of time, converts it to data
    inputs: stream, PyAudio object
    outputs: int16 data array
    """

    input_data = stream.read(CHUNK_SIZE)
    data = np.frombuffer(input_data, np.int16)
    return data


def get_sample(stream: pyaudio.Stream) -> np.ndarray:
    """
    get_sample:
    gets the audio data from the microphone
    inputs: audio stream and PyAudio object
    outputs: int16 array"""

    data = get_data(stream)
    return data


class AudioMic:
    def __init__(self, open=False):
        self.stream = None
        self.pa = None
        if open:
            self.open()

    def open(self):
        if self.stream is not None or self.pa is not None:
            raise RuntimeError("Opening an open mic.")
        stream, pa = _open_mic()
        self.stream = stream
        self.pa = pa

    def read(self):
        return get_sample(self.stream)

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