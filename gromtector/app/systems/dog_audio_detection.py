from datetime import datetime, timezone
import logging
from typing import Sequence
from .BaseSystem import BaseSystem


logger = logging.getLogger(__name__)

_DOG_NOISE_OF_INTEREST = [
    "Bark",
    "Whimper (dog)",
    "Growling",
    "Howl",
    "Yip",
]

_ANIMAL_CLASSES_OF_INTEREST = [
    "Dog",
    "Canidae, dogs, wolves",
    "Domestic animals, pets",
    "Wild animals",
    "Livestock, farm animals, working animals",
    "Animal",
]

_CLASSES_OF_INTEREST = _ANIMAL_CLASSES_OF_INTEREST + _DOG_NOISE_OF_INTEREST

CLASSES_OF_INTEREST = [s.lower() for s in _CLASSES_OF_INTEREST]
ANIMAL_CLASSES_OF_INTEREST = [s.lower() for s in _ANIMAL_CLASSES_OF_INTEREST]
DOG_NOISE_OF_INTEREST = [s.lower() for s in _DOG_NOISE_OF_INTEREST]


class DogAudioDetectionSystem(BaseSystem):
    raw_detection_begin_timestamp: datetime = None
    raw_detection_end_timestamp: datetime = None
    last_raw_bark_end_timestamp: datetime = None
    initial_trigger_classes: Sequence = None

    def init(self) -> None:
        evt_mgr = self.get_event_manager()
        evt_mgr.add_listener("detected_classes", self.recv_dclasses)

        configs = self.get_config()
        self.animal_class_threshold: float = float(configs["--dog-class-threshold"])
        self.dog_audio_class_threshold: float = float(configs["--dog-audio-class-threshold"])

        logger.info("Dog class threshold: %.2f", self.animal_class_threshold)
        logger.info("Dog audio class threshold: %.2f", self.dog_audio_class_threshold)

    def recv_dclasses(self, event_type, event) -> None:
        evt_mgr = self.get_event_manager()

        detected_classes = event["classes"]
        detected_dog_classes = [
            c
            for c in detected_classes
            if c["label"].lower() in ANIMAL_CLASSES_OF_INTEREST and c["score"] >= self.animal_class_threshold
        ]
        detected_dog_noise_classes = [
            c
            for c in detected_classes
            if c["label"].lower() in DOG_NOISE_OF_INTEREST and c["score"] >= self.dog_audio_class_threshold
        ]
        if len(detected_dog_classes) > 2 and detected_dog_noise_classes:
            self.raw_detection_end_timestamp = None
            if self.raw_detection_begin_timestamp is None:
                self.raw_detection_begin_timestamp = event["begin_timestamp"]
                self.initial_trigger_classes = (
                    detected_dog_classes + detected_dog_noise_classes
                )

                evt_mgr.queue_event(
                    "dog_bark_begin",
                    {
                        "begin_timestamp": self.raw_detection_begin_timestamp,
                        "detected_classes": self.initial_trigger_classes,
                        "dog_class_threshold": self.animal_class_threshold,
                        "dog_audio_class_threshold": self.dog_audio_class_threshold,
                    },
                )
            else:
                # on-going barking.
                pass

        else:
            if (
                self.raw_detection_begin_timestamp is not None
                and self.last_raw_bark_end_timestamp is None
            ):
                # barking stopped.
                self.last_raw_bark_end_timestamp = datetime.now(tz=timezone.utc)

    def update(self, elapsed_time_ms: int) -> None:
        evt_mgr = self.get_event_manager()

        if self.last_raw_bark_end_timestamp is not None:
            now = datetime.now(tz=timezone.utc)
            dur_since_last_raw_bark_end = now - self.last_raw_bark_end_timestamp
            wait_s = 1.0
            if dur_since_last_raw_bark_end.seconds >= wait_s:
                self.raw_detection_end_timestamp = self.last_raw_bark_end_timestamp

                evt_mgr.queue_event(
                    "audio_event_dogbark",
                    {
                        "begin_timestamp": self.raw_detection_begin_timestamp,
                        "end_timestamp": self.raw_detection_end_timestamp,
                        "trigger_classes": self.initial_trigger_classes,
                        "dog_class_threshold": self.animal_class_threshold,
                        "dog_audio_class_threshold": self.dog_audio_class_threshold,
                    },
                )

                evt_mgr.queue_event(
                    "dog_bark_end",
                    {
                        "end_timestamp": self.raw_detection_end_timestamp,
                        "dog_class_threshold": self.animal_class_threshold,
                        "dog_audio_class_threshold": self.dog_audio_class_threshold,
                    },
                )

                self.last_raw_bark_end_timestamp = None
                self.raw_detection_begin_timestamp = None
                self.raw_detection_end_timestamp = None
                self.initial_trigger_classes = None
