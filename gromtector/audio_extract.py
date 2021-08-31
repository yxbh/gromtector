import glob
from gromtector import app
import os
import logging
from pathlib import Path

import audiosegment as ad

logger = logging.getLogger(__name__)


def extract_audio_inplace(args: dict) -> None:
    src_audio_paths = []
    input_path = Path(args["<AUDIO_PATH>"])
    logger.debug(f"Input path: {input_path}")

    if input_path.is_dir():
        supported_extensions = ["m4a", "mp4"]
        for ext in supported_extensions:
            for ip in input_path.glob("*.{}".format(ext)):
                src_audio_paths.append(ip)

    for input_file_path in src_audio_paths:
        logger.info(f"Extracting audio from {input_file_path}")
        seg = ad.from_file(input_file_path)
        target_dir = input_file_path.parent
        src_filename = input_file_path.name
        src_fname, src_fext = os.path.splitext(src_filename)
        seg = seg.resample(
            channels=1,
            sample_rate_Hz=16000,
            sample_width=2,
        )
        seg.export(f"{target_dir / src_fname}.wav".format(src_fname), format="wav")
