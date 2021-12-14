"""
gromtector

Usage:
  gromtector
    [--file=<INPUT_FILE>]
    [--tf-model=<MODEL_PATH>] [--graph-palette=<GRAPH_PALETTE>]
    [--dog-class-threshold=<DCTH> --dog-audio-class-threshold=<DACTH>]
    [--bark-response-audio=<BARKRA>... --bark-notify-email=<BARKNE> --gmail-app-pw=<GMAIL_PW>]
    [--server-mode | --client-mode=<SERVER_IP>]
    [--max-fps=<MAX_FPS>] [--log-level=<log_lvl>]
  gromtector extract <AUDIO_PATH> [--log-level=<log_lvl>]
  gromtector -h | --help

Options:
  --file=<INPUT_FILE>       Input audio/video file path. The app runs on the input file instead of streaming audio from a live mic.
  --tf-model=<MODEL_PATH>   Tensorflow audio classification model path.
  --graph-palette=<GRAPH_PALETTE>       Optional palette name for graphs.
  --dog-class-threshold=<DCTH>          Inference threshold for detecting dog classes [default: 0.9].
  --dog-audio-class-threshold=<DACTH>   Inference threshold for detecting dog audio classes [default: 0.85].
  --bark-response-audio=<BARKRA>        The audio to playback when Gromit's barking is detected.
  --bark-notify-email=<BARKNE>          Email address to send email when Gromit's barking is detected.
  --gmail-app-pw=<GMAIL_PW>             Gmail app password for sending email notifications.
  --server-mode                         Run Gromtector in server mode.
  --client-mode=<SERVER_IP>             Run Gromtector in client mode connecting to the given server.
  --max-fps=<MAX_FPS>       Set the max app FPS [default: 60].
  --log-level=<log_lvl>     Logging level.
  -h --help                 Show this screen.
"""

import logging
import os
import platform

from docopt import docopt


from gromtector.app import Application
from gromtector.app.systems.debug import DebugSystem
from gromtector.app.systems.keyboard import KeyboardSystem
from gromtector.app.systems.mic import AudioMicSystem
from gromtector.app.systems.audio_file import AudioFileSystem
from gromtector.app.systems.mq_system import MqSystem
from gromtector.app.systems.spectrogram import SpectrogramSystem
from gromtector.app.systems.sgram_graph import SpectrogramGraphSystem
from gromtector.app.systems.hud import HudSystem
from gromtector.app.systems.tf_yamnet import TfYamnetSystem
from gromtector.app.systems.dog_audio_detection import DogAudioDetectionSystem
from gromtector.app.systems.bark_react import BarkReactSystem

from gromtector.audio_extract import extract_audio_inplace

from gromtector.logging import FORMAT

logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)


def main():
    cli_params = docopt(__doc__)
    if cli_params["--log-level"]:
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        for ll in loggers:
            ll.setLevel(cli_params["--log-level"].upper())
    logger.debug(cli_params)

    logger.debug("Hello World")

    if cli_params["extract"]:
        extract_audio_inplace(cli_params)

    else:
        system_classes = [
            KeyboardSystem,
        ]

        if cli_params["--file"]:
            system_classes += [
                AudioFileSystem,
            ]
        elif cli_params["--client-mode"] or (
            not cli_params["--server-mode"] and not cli_params["--client-mode"]
        ):
            system_classes += [
                AudioMicSystem,
            ]
        system_classes += [
            DebugSystem,
            SpectrogramSystem,
            SpectrogramGraphSystem,
            DogAudioDetectionSystem,
            BarkReactSystem,
            HudSystem,
        ]
        if cli_params["--server-mode"] or cli_params["--client-mode"]:
            system_classes += [
                MqSystem,
                # TcpCommSystem,
            ]

        if cli_params["--tf-model"] and not cli_params["--client-mode"]:
            system_classes += [
                TfYamnetSystem,
            ]

        app = Application(
            args=cli_params,
            system_classes=system_classes,
        )
        app.run()

    logger.debug("Bye World")
