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
from matplotlib.figure import Figure

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LogNorm, Normalize
from matplotlib.image import AxesImage
from typing import Tuple

from gromtector.audio_mic import AudioMic, open_mic
from gromtector.spectrogram import get_spectrogram
from gromtector import logger


MAX_VAL = -(2 ** 32)
MIN_VAL = 2 ** 32
MOD_SPEC = True


def update_fig(
    frame: int, im: AxesImage, mic: AudioMic, file_fig: Figure, file_im: AxesImage
) -> Tuple[AxesImage]:
    """
    updates the image, just adds on samples at the start until the maximum size is
    reached, at which point it 'scrolls' horizontally by determining how much of the
    data needs to stay, shifting it left, and appending the new data.
    inputs: iteration number
    outputs: updated image
    """
    data = mic.read()
    arr_2d, freqs, times = get_spectrogram(data, mic.sample_rate, mod_spec=MOD_SPEC)
    im_data = im.get_array()

    global MAX_VAL, MIN_VAL
    cur_max = arr_2d.max()
    if cur_max > MAX_VAL:
        MAX_VAL = cur_max
        logger.debug("New max: {}, ({}, {})".format(MAX_VAL, MIN_VAL, MAX_VAL))
    cur_min = arr_2d.min()
    if cur_min < MIN_VAL:
        MIN_VAL = cur_min
        logger.debug("New min: {}, ({}, {})".format(MIN_VAL, MIN_VAL, MAX_VAL))

    # frame cannot be relied upon: we're called multiple times with 0 before it
    # starts to increment.
    frame = im_data.shape[1] // len(times)  # current number of frames in the image now.

    max_num_frames = 1 / times[-1]
    if frame < max_num_frames:
        im_data = np.hstack((im_data, arr_2d))
    else:
        im_data = np.hstack(
            (
                im_data[:, len(times) :],
                arr_2d,
            )
        )
    im.set_data(im_data)

    # file_im.set_data(im_data)
    # file_fig.savefig(
    #     "test_output.png",
    #     bbox_inches="tight",
    #     transparent=True,
    #     pad_inches=0,
    #     frameon="false",
    # )

    return (im,)


def make_plot(mic: AudioMic) -> FuncAnimation:
    # Initialize Plot
    fig = plt.figure()
    ax = fig.gca()

    # Data for first frame
    data = mic.read()
    arr_2d, freqs, times = get_spectrogram(data, mic.sample_rate, mod_spec=MOD_SPEC)
    logger.debug("spectrum shape:\n{}".format(arr_2d.shape))
    logger.debug("spectrum:\n{}".format(arr_2d[0]))
    logger.debug("freqs shape:\n{}".format(freqs.shape))
    logger.debug("freqs:\n{}".format(freqs))
    logger.debug("times shape:\n{}".format(times.shape))
    logger.debug("times:\n{}".format(times))

    logger.debug("time length: {}".format(len(times)))
    logger.debug("time avg (ms): {}".format(sum(times) / len(times)))

    # Set up the plot parameters
    extent = (0, 1, freqs[-1], freqs[0])
    # vmin = arr_2d.min()
    # vmax = arr_2d.max()
    vmin = 1e-7
    vmax = 1.0
    norm = LogNorm(vmin=vmin, vmax=vmax)
    norm = Normalize(vmin=-200.0, vmax=200.0)
    im = ax.imshow(
        arr_2d,
        aspect="auto",
        extent=extent,
        interpolation="none",
        cmap="jet",
        norm=norm,
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title("Real-Time Spectogram")
    ax.invert_yaxis()
    fig.colorbar(im)  # enable if you want to display a color bar

    file_fig = None
    file_im = None

    # file_fig = plt.figure("file_fig")
    # file_fig_ax = file_fig.gca()
    # file_im = file_fig_ax.imshow(
    #     arr_2d,
    #     aspect="auto",
    #     extent=extent,
    #     interpolation="none",
    #     cmap="jet",
    #     norm=norm,
    # )
    # file_fig_ax.axis("off")
    # file_fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    # file_fig_ax.invert_yaxis()
    # file_fig.savefig(
    #     "test_output.png",
    #     bbox_inches="tight",
    #     transparent=True,
    #     pad_inches=0,
    # )

    # Animate
    return FuncAnimation(
        fig,
        func=update_fig,
        fargs=(im, mic, file_fig, file_im),
        interval=mic.desireable_sample_length,
        blit=True,
    )


def main():
    cli_params = docopt(__doc__)
    if cli_params["--log-level"]:
        logger.setLevel(cli_params["--log-level"].upper())
    logger.debug(cli_params)

    logger.debug("Hello World")
    with open_mic(chunk_size=4096) as mic:
        animation = make_plot(mic)
        plt.show()
