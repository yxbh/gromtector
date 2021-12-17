from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Any, Mapping, Sequence

from gromtector.app.events import (
    AudioEventDogBarkEvent,
    DetectedObjectClassesEvent,
    DogBarkBeganEvent,
    DogBarkEndedEvent,
)
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
    raw_detection_begin_ts_by_ids: Mapping[Any, datetime] = defaultdict(lambda: None)
    raw_detection_end_ts_by_ids: Mapping[Any, datetime] = defaultdict(lambda: None)
    last_raw_bark_end_ts_by_ids: Mapping[Any, datetime] = defaultdict(lambda: None)
    initial_trigger_classes_by_ids: Mapping[Any, Sequence] = defaultdict(list)

    def init(self) -> None:
        evt_mgr = self.get_event_manager()
        evt_mgr.add_listener(DetectedObjectClassesEvent.EVENT_TYPE, self.recv_dclasses)

        configs = self.get_config()
        self.animal_class_threshold = float(configs["--dog-class-threshold"])
        self.dog_audio_class_threshold = float(configs["--dog-audio-class-threshold"])

        logger.info("Dog class threshold: %.2f", self.animal_class_threshold)
        logger.info("Dog audio class threshold: %.2f", self.dog_audio_class_threshold)

    def recv_dclasses(self, event_type, event: DetectedObjectClassesEvent) -> None:
        evt_mgr = self.get_event_manager()
        id = event.client_id

        detected_classes = event.classes
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
            # logger.debug("Dog sound YES YES YES")
            self.raw_detection_end_ts_by_ids[id] = None
            if self.raw_detection_begin_ts_by_ids[id] is None:
                self.raw_detection_begin_ts_by_ids[id] = event.begin_timestamp
                self.initial_trigger_classes_by_ids[id] = (
                    detected_dog_classes + detected_dog_noise_classes
                )

                evt_mgr.queue_event(
                    DogBarkBeganEvent.EVENT_TYPE,
                    DogBarkBeganEvent(
                        begin_timestamp=self.raw_detection_begin_ts_by_ids[id],
                        detected_classes=self.initial_trigger_classes_by_ids[id],
                        dog_class_threshold=self.animal_class_threshold,
                        dog_audio_class_threshold=self.dog_audio_class_threshold,
                        client_id=event.client_id,
                    ),
                )
            else:
                # on-going barking.
                pass

        else:
            if (
                self.raw_detection_begin_ts_by_ids[id] is not None
                and self.last_raw_bark_end_ts_by_ids[id] is None
            ):
                # barking stopped.
                self.last_raw_bark_end_ts_by_ids[id] = datetime.now(tz=timezone.utc)

    def update(self, elapsed_time_ms: int) -> None:
        evt_mgr = self.get_event_manager()

        for id, last_raw_bark_end_timestamp in list(
            self.last_raw_bark_end_ts_by_ids.items()
        ):
            if last_raw_bark_end_timestamp is not None:
                now = datetime.now(tz=timezone.utc)
                dur_since_last_raw_bark_end = now - last_raw_bark_end_timestamp
                wait_s = 1.0
                if dur_since_last_raw_bark_end.seconds >= wait_s:
                    self.raw_detection_end_ts_by_ids[id] = last_raw_bark_end_timestamp

                    evt_mgr.queue_event(
                        AudioEventDogBarkEvent.EVENT_TYPE,
                        AudioEventDogBarkEvent(
                            begin_timestamp=self.raw_detection_begin_ts_by_ids[id],
                            end_timestamp=self.raw_detection_end_ts_by_ids[id],
                            trigger_classes=self.initial_trigger_classes_by_ids[id],
                            dog_class_threshold=self.animal_class_threshold,
                            dog_audio_class_threshold=self.dog_audio_class_threshold,
                            client_id=id,
                        ),
                    )

                    evt_mgr.queue_event(
                        DogBarkEndedEvent.EVENT_TYPE,
                        DogBarkEndedEvent(
                            end_timestamp=self.raw_detection_end_ts_by_ids[id],
                            client_id=id,
                        ),
                    )

                    self.last_raw_bark_end_ts_by_ids[id] = None
                    self.raw_detection_begin_ts_by_ids[id] = None
                    self.raw_detection_end_ts_by_ids[id] = None
                    self.initial_trigger_classes_by_ids[id] = None
