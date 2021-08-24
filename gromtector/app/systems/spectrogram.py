import logging
import numpy as np

from .BaseSystem import BaseSystem

from gromtector.spectrogram import get_spectrogram

logger = logging.getLogger(__name__)


class SpectrogramSystem(BaseSystem):
    def init(self):
        self.get_event_manager().add_listener(
            "new_audio_data", self.receive_audio_data
        )

        self.audio_data_buffer = None
        self.sample_rate = None
        self.sample_interval_to_keep_s = 2.0

    def receive_audio_data(self, event_type, audio_mic_evt):
        self.sample_rate = audio_mic_evt.rate
        if self.audio_data_buffer is None:
            self.audio_data_buffer = audio_mic_evt.data
        else:
            self.audio_data_buffer = np.concatenate(
                [self.audio_data_buffer, audio_mic_evt.data]
            )
        num_samples_to_keep = int(self.sample_rate * self.sample_interval_to_keep_s)
        self.audio_data_buffer = self.audio_data_buffer[-num_samples_to_keep:]

        # logger.debug("Received {} len of audio data.".format(len(audio_mic_data)))

    def update(self, elapsed_time_ms: int) -> None:
        if self.audio_data_buffer is None:
            return

        # logger.debug("{}ms elapsed.".format(elapsed_time_ms))
        Sxx, freqs, times = get_spectrogram(
            signal=self.audio_data_buffer,
            rate=self.sample_rate,
            mod_spec=True,
            nfft=512,
        )
        self.get_event_manager().queue_event(
            "new_spectrogram_info",
            {
                "new_spectrum_shape": Sxx.shape,
                "new_frequencies_shape": freqs.shape,
                "new_times_shape": times.shape,
                "new_max_time": times[-1],
            },
        )
        self.get_event_manager().queue_event(
            "new_spectrogram",
            {
                "signals": Sxx,
                "frequencies": freqs,
                "times": times,
            },
        )

        # logger.debug("spectrum shape:\n{}".format(Sxx.shape))
        # logger.debug("spectrum:\n{}".format(Sxx[0]))
        # logger.debug("freqs shape:\n{}".format(freqs.shape))
        # logger.debug("freqs:\n{}".format(freqs))
        # logger.debug("times shape:\n{}".format(times.shape))
        # logger.debug("times:\n{}".format(times))
