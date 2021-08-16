from typing import Tuple
import numpy as np
from matplotlib.mlab import window_hanning, specgram
import scipy.signal as scipy_signal

NFFT = 256  # 256 #1024 #NFFT value for spectrogram
OVERLAP = 196  # 512 #overlap value for spectrogram
OVERLAP = NFFT / 2


def get_spectrogram_scipy(
    signal, rate, mod_spec=False
) -> Tuple[
    np.ndarray,  # 2D spectrum
    np.ndarray,  # Frequency axis
    np.ndarray,  # Time axis
]:
    f, t, Sxx = scipy_signal.spectrogram(signal, rate)
    if mod_spec:
        Sxx = Sxx / NFFT
        Sxx = 10 * np.log10(Sxx)
    return Sxx, f, t


def get_spectrogram_plt(
    signal, rate, mod_spec=False
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
    if mod_spec:
        arr2D = arr2D / NFFT
        # arr2D = arr2D / arr2D.max()
        arr2D = 10 * np.log10(arr2D)
    return arr2D, freqs, bins


def get_spectrogram(
    signal, rate, mod_spec=False
) -> Tuple[
    np.ndarray,  # 2D spectrum
    np.ndarray,  # Frequency axis
    np.ndarray,  # Time axis
]:
    return get_spectrogram_scipy(signal, rate, mod_spec)
    # return get_spectrogram_plt(signal, rate, mod_spec)
