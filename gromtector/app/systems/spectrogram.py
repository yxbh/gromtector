import logging

from .BaseSystem import BaseSystem

from gromtector.spectrogram import get_spectrogram

logger = logging.getLogger(__name__)


class SpectrogramSystem(BaseSystem):
    def init(self):
        self.get_event_manager().add_listener("new_audio_mic_data", self.test)

    def test(self, event_type, audio_mic_evt):
        # logger.debug("Received {} len of audio data.".format(len(audio_mic_data)))
        Sxx, freqs, times = get_spectrogram(
            signal=audio_mic_evt.data, rate=audio_mic_evt.rate, mod_spec=True
        )
        logger.debug("spectrum shape:\n{}".format(Sxx.shape))
        logger.debug("spectrum:\n{}".format(Sxx[0]))
        logger.debug("freqs shape:\n{}".format(freqs.shape))
        logger.debug("freqs:\n{}".format(freqs))
        logger.debug("times shape:\n{}".format(times.shape))
        logger.debug("times:\n{}".format(times))

    def update(self, elapsed_time_ms: int) -> None:
        # logger.debug("{}ms elapsed.".format(elapsed_time_ms))
        pass
