from contextlib import contextmanager
from random import sample
from typing import Dict, Tuple, ByteString
import logging

import pyaudio
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_WIDTH = 2  # pyaudio.paInt16  # conversion format for PyAudio stream
DEFAULT_CHANNELS = 1  # microphone audio channels
DEFAULT_SAMPLE_RATE = 48_000  # num audio sample per sec
DEFAULT_SAMPLE_RATE = 44_100
DEFAULT_CHUNK_SIZE = 8192  # number of samples to take per read

# SAMPLE_LENGTH = int(CHUNK_SIZE * 1_000 / SAMPLE_RATE)  # length of each sample in ms
DEFAULT_SAMPLE_PER_MS = DEFAULT_SAMPLE_RATE / 1000  # sample per ms
DEFAULT_SAMPLE_LENGTH = int(
    DEFAULT_CHUNK_SIZE / DEFAULT_SAMPLE_PER_MS
)  # chunk duration.


def _open_mic(sample_rate, channels, chunk_size, sample_width):
    """
    open_mic:
    creates a PyAudio object and initializes the mic stream
    inputs: none
    ouputs: stream, PyAudio object
    """

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.get_format_from_width(sample_width),
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_size,
    )
    return stream, pa


def _open_callback_mic(sample_rate, channels, sample_width, callback):
    """
    open_mic:
    creates a PyAudio object and initializes the mic stream
    inputs: none
    ouputs: stream, PyAudio object
    """

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.get_format_from_width(sample_width),
        channels=channels,
        rate=sample_rate,
        input=True,
        # frames_per_buffer=chunk_size,
        stream_callback=callback,
    )
    return stream, pa


def get_data(stream: pyaudio.Stream, chunk_size: int = 0) -> np.ndarray:
    """
    get_data:
    reads from the audio stream for a constant length of time, converts it to data
    inputs: stream, PyAudio object
    outputs: int16 data array
    """
    num_frames = chunk_size if chunk_size else stream.get_read_available()
    input_data = stream.read(num_frames, exception_on_overflow=False)
    data = np.frombuffer(input_data, np.int16)
    return data


def get_sample(stream: pyaudio.Stream, chunk_size: int = 0) -> np.ndarray:
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
        self.sample_width = DEFAULT_SAMPLE_WIDTH
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
            sample_width=self.sample_width,
        )
        self.stream = stream
        self.pa = pa

    def read(self):
        return get_sample(self.stream, self.chunk_size)

    def get_desireable_sample_interval_ms(self):
        sample_per_ms = self.sample_rate / 1000  # sample per ms
        sample_length = int(
            self.chunk_size / self.sample_width / sample_per_ms
        )  # chunk duration.
        return sample_length

    @property
    def desireable_sample_interval_ms(self):
        return self.get_desireable_sample_interval_ms()

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
def open_mic(chunk_size=None):
    try:
        mic = AudioMic(chunk_size=chunk_size)
        mic.open()
        yield mic
    finally:
        mic.close()


class CallbackAudioMic:
    def __init__(self, open=False, sample_rate=None, channels=None):
        self.sample_rate = sample_rate if sample_rate else DEFAULT_SAMPLE_RATE
        self.channels = channels if channels else DEFAULT_CHANNELS
        self.sample_width = DEFAULT_SAMPLE_WIDTH
        self.stream = None
        self.pa = None
        if open:
            self.open()

    def callback(
        self,
        input_data: ByteString,
        frame_count: int,
        time_info: dict,
        status_flag: int,
    ) -> Tuple[ByteString, int]:
        """
        callback(
            in_data,      # recorded data if input=True; else None
            frame_count,  # number of frames
            time_info,    # dictionary
            status_flags) # PaCallbackFlags

        Returns `(out_data, flag)`

        `time_info` is a dictionary with the following keys: `input_buffer_adc_time`, `current_time`, and `output_buffer_dac_time`; see the PortAudio documentation for their meanings.
        `status_flags` is one of PortAutio Callback Flag.

        `out_data` is a byte array whose length should be the `(frame_count * channels * bytes-per-channel)` if `output=True` or `None` if `output=False`.
        flag must be either paContinue, paComplete or paAbort (one of PortAudio Callback Return Code).
        When `output=True` and `out_data` does not contain at least `frame_count` frames, `paComplete` is assumed for flag.
        """
        # logger.debug("CallbackAudioMic callback()")
        self.buffer += input_data
        out_data = input_data
        # logger.debug("Mic flag: {}".format(status_flag))
        if status_flag in [
            pyaudio.paInputUnderflow,
            pyaudio.paInputOverflow,
        ]:
            logger.warning("Some sort of audio mic input overflow/underflow has occurred.")
        return (out_data, pyaudio.paContinue)

    def open(self):
        if self.stream is not None or self.pa is not None:
            raise RuntimeError("Opening an open mic.")
        stream, pa = _open_callback_mic(
            sample_rate=self.sample_rate,
            channels=self.channels,
            sample_width=self.sample_width,
            callback=self.callback,
        )
        self.stream = stream
        self.pa = pa
        self.stream.start_stream()
        self.buffer = b""

    def read(self):
        buf = np.frombuffer(self.buffer, dtype=np.int16)
        self.buffer = b""
        return buf

    def get_desireable_sample_interval_ms(self):
        sample_per_ms = self.sample_rate / 1000  # sample per ms
        sample_length = int(
            self.chunk_size / self.sample_width / sample_per_ms
        )  # chunk duration.
        return sample_length

    @property
    def desireable_sample_interval_ms(self):
        return self.get_desireable_sample_interval_ms()

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
