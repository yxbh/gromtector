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


from gromtector.app.application import Application
from gromtector.app.systems.debug import DebugSystem
from gromtector.app.systems.mic import AudioMicSystem
from gromtector.app.systems.spectrogram import SpectrogramSystem

from gromtector.logging import FORMAT
from gromtector.app import Application

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

    app = Application(
        args=cli_params,
        system_classes=[
            DebugSystem,
            AudioMicSystem,
            SpectrogramSystem,
        ],
    )
    app.run()

    logger.debug("Bye World")
