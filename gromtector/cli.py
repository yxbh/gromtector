"""
gromtector

Usage:
  gromtector [--file=<INPUT_FILE>] [--log-level=<log_lvl>]
  gromtector -h | --help

Options:
  --file=<INPUT_FILE>       Input audio/video file path.
  --log-level=<log_lvl>     Logging level.
  -h --help                 Show this screen.
"""
import os
import platform

from docopt import docopt

import numpy as np

from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LogNorm, Normalize
from matplotlib.image import AxesImage
from typing import Tuple

import pyaudio

from gromtector.audio_file import AudioFile
from gromtector.audio_mic import AudioMic, open_mic
from gromtector.spectrogram import get_spectrogram
from gromtector import logger


MAX_VAL = -(2 ** 32)
MIN_VAL = 2 ** 32
MOD_SPEC = True

MAX_PLOT_PERIOD_SEC = 1.0

AUDIO_OUTPUT = None
AUDIO_OUTPUT_STREAM = None


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

    max_num_frames = MAX_PLOT_PERIOD_SEC / times[-1]
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

    if AUDIO_OUTPUT_STREAM:
        AUDIO_OUTPUT_STREAM.write(data)

    # file_im.set_data(im_data)
    # file_fig.savefig(
    #     "test_output.png",
    #     bbox_inches="tight",
    #     transparent=True,
    #     pad_inches=0,
    #     frameon="false",
    # )

    # logger.debug("Frame")

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
    extent = (0, MAX_PLOT_PERIOD_SEC, freqs[-1], freqs[0])
    norm = LogNorm(vmin=1e-7, vmax=1.0)
    norm = Normalize(vmin=-40.0, vmax=40.0)
    im = ax.imshow(
        arr_2d,
        aspect="auto",
        extent=extent,
        interpolation="none",
        cmap="inferno",
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

    global AUDIO_OUTPUT_STREAM
    if AUDIO_OUTPUT_STREAM:
        AUDIO_OUTPUT_STREAM.write(data.tobytes())

    animate_interval_ms = mic.desireable_sample_interval_ms
    logger.debug("Animation interval (ms): {}".format(animate_interval_ms))

    # Animate
    return FuncAnimation(
        fig,
        func=update_fig,
        fargs=(im, mic, file_fig, file_im),
        interval=animate_interval_ms,
        blit=True,
    )


def main():
    cli_params = docopt(__doc__)
    if cli_params["--log-level"]:
        logger.setLevel(cli_params["--log-level"].upper())
    logger.debug(cli_params)

    logger.debug("Hello World")

    if cli_params["--file"]:
        input_file_path = cli_params["--file"]
        if platform.system() == "Darwin" and input_file_path.startswith("~"):
            input_file_path = os.path.expanduser(input_file_path)
        aud_input = AudioFile(file_path=input_file_path, chunk_size=4096)

        global AUDIO_OUTPUT, AUDIO_OUTPUT_STREAM
        AUDIO_OUTPUT = pyaudio.PyAudio()
        AUDIO_OUTPUT_STREAM = AUDIO_OUTPUT.open(
            format=AUDIO_OUTPUT.get_format_from_width(
                aud_input.audio_segment.seg.sample_width,  # or maybe frame_width?
            ),
            channels=aud_input.audio_segment.channels,
            rate=aud_input.audio_segment.frame_rate,
            output=True,
        )

        animation = make_plot(aud_input)
        plt.show()
        AUDIO_OUTPUT_STREAM.stop_stream()
        AUDIO_OUTPUT_STREAM.close()
        AUDIO_OUTPUT.terminate()

    else:
        with open_mic(chunk_size=4096) as aud_input:
            animation = make_plot(aud_input)
            plt.show()

    logger.debug("Bye World")
