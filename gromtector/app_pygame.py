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
import logging
import os
import platform

from docopt import docopt


from gromtector.app import Application
from gromtector.app.systems.debug import DebugSystem
from gromtector.app.systems.mic import AudioMicSystem
from gromtector.app.systems.audio_file import AudioFileSystem
from gromtector.app.systems.spectrogram import SpectrogramSystem
from gromtector.app.systems.sgram_graph import SpectrogramGraphSystem
from gromtector.app.systems.hud import HudSystem

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

    if cli_params["--file"]:
        system_classes = [
            AudioFileSystem,
        ]
    else:
        system_classes = [
            AudioMicSystem,
        ]
    system_classes += [
        DebugSystem,
        SpectrogramSystem,
        SpectrogramGraphSystem,
        HudSystem,
    ]

    app = Application(
        args=cli_params,
        system_classes=system_classes,
    )
    app.run()

    logger.debug("Bye World")
