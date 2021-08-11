from typing import Tuple
import numpy as np
from matplotlib.mlab import window_hanning, specgram

NFFT = 256  # 256 #1024 #NFFT value for spectrogram
OVERLAP = 196  # 512 #overlap value for spectrogram
OVERLAP = NFFT / 2


def get_spectrogram(
    signal, rate
) -> Tuple[
    np.ndarray,  # 2D spectrum
    np.ndarray,  # Frequency axis
    np.ndarray,  # Time axis
]:
    """
    get_specgram:
    takes the FFT to create a spectrogram of the given audio signal
    input: audio signal, sampling rate
    output: 2D Spectrogram Array, Frequency Array, Bin Array
    see matplotlib.mlab.specgram documentation for help"""

    arr2D, freqs, bins = specgram(
        signal, window=window_hanning, Fs=rate, NFFT=NFFT, noverlap=OVERLAP
    )
    return arr2D, freqs, bins
