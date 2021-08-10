"""
gromtector

Usage:
  gromtector [--log-level=<log_lvl>]
  gromtector -h | --help

Options:
  --log-level=<log_lvl>     Logging level.
  -h --help                 Show this screen.
"""
from docopt import docopt

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LogNorm
from matplotlib.image import AxesImage
from typing import Tuple

from gromtector.audio_mic import SAMPLE_LENGTH, SAMPLE_RATE

from gromtector.audio_mic import AudioMic, open_mic
from gromtector.spectrogram import get_spectrogram
from gromtector import logger


SAMPLES_PER_FRAME = 5  # Number of mic reads concatenated within a single window



def update_fig(frame: int, im: AxesImage, mic: AudioMic) -> Tuple[AxesImage]:
    """
    updates the image, just adds on samples at the start until the maximum size is
    reached, at which point it 'scrolls' horizontally by determining how much of the
    data needs to stay, shifting it left, and appending the new data.
    inputs: iteration number
    outputs: updated image
    """
    data = mic.read()
    arr_2d, freqs, times = get_spectrogram(data, SAMPLE_RATE)
    im_data = im.get_array()

    # frame cannot be relied upon: we're called multiple times with 0 before it
    # starts to increment.
    frame = im_data.shape[1] // len(times)

    if frame < SAMPLES_PER_FRAME:
        im_data = np.hstack((im_data, arr_2d))
        im.set_array(im_data)
    else:
        im_data = np.hstack((
            im_data[:, len(times):],
            arr_2d,
        ))
        im.set_array(im_data)

    return im,


def make_plot(mic: AudioMic) -> FuncAnimation:
    # Initialize Plot
    fig = plt.figure()
    ax = fig.gca()

    # Data for first frame
    data = mic.read()
    arr_2d, freqs, times = get_spectrogram(data, SAMPLE_RATE)

    # Set up the plot parameters
    extent = (times[0], times[-1]*SAMPLES_PER_FRAME, freqs[-1], freqs[0])
    im = ax.imshow(arr_2d, aspect='auto', extent=extent, interpolation='none',
                   cmap='jet', norm=LogNorm(vmin=.01, vmax=1))
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_title('Real-Time Spectogram')
    ax.invert_yaxis()
    # fig.colorbar(im)  # enable if you want to display a color bar

    # Animate
    return FuncAnimation(
        fig,
        func=update_fig, fargs=(im, mic),
        interval=SAMPLE_LENGTH,
        blit=True,
    )


def main():
    cli_params = docopt(__doc__)
    if cli_params["--log-level"]:
        logger.setLevel(cli_params["--log-level"].upper())
    logger.debug(cli_params)

    logger.debug("Hello World")
    with open_mic() as mic:
        animation = make_plot(mic)
        plt.show()
