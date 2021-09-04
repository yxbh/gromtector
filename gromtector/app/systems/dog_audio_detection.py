from datetime import datetime
from .BaseSystem import BaseSystem


_CLASSES_OF_INTEREST = [
    "Dog",
    "Canidae, dogs, wolves",
    "Domestic animals, pets",
    "Wild animals",
    "Livestock, farm animals, working animals",
    "Animal",
    "Bark",
    "Whimper (dog)",
    "Growling",
    "Howl",
    "Yip",
]

CLASSES_OF_INTEREST = [s.lower() for s in _CLASSES_OF_INTEREST]


class DogAudioDetectionSystem(BaseSystem):
    raw_detection_begin_timestamp: datetime = None
    raw_detection_end_timestamp: datetime = None
    last_raw_bark_end_timestamp: datetime = None

    def init(self) -> None:
        evt_mgr = self.get_event_manager()
        evt_mgr.add_listener("detected_classes", self.recv_dclasses)

    def recv_dclasses(self, event_type, event) -> None:
        evt_mgr = self.get_event_manager()

        detected_classes = event["classes"]
        detected_dog_classes = [
            c for c in detected_classes if c["label"].lower() in CLASSES_OF_INTEREST
        ]
        detected_dog_classes = [c for c in detected_dog_classes if c["score"] > 0.4]
        dog_bark_detected = len(detected_dog_classes) > 2
        if dog_bark_detected:
            self.raw_detection_end_timestamp = None
            if self.raw_detection_begin_timestamp is None:
                self.raw_detection_begin_timestamp = event["begin_timestamp"]

                evt_mgr.queue_event(
                    "dog_bark_begin",
                    {
                        "begin_timestamp": self.raw_detection_begin_timestamp,
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
                self.last_raw_bark_end_timestamp = datetime.utcnow()

    def update(self, elapsed_time_ms: int) -> None:
        evt_mgr = self.get_event_manager()

        if self.last_raw_bark_end_timestamp is not None:
            now = datetime.utcnow()
            dur_since_last_raw_bark_end = now - self.last_raw_bark_end_timestamp
            wait_s = 1.0
            if dur_since_last_raw_bark_end.seconds >= wait_s:
                self.raw_detection_end_timestamp = self.last_raw_bark_end_timestamp

                evt_mgr.queue_event(
                    "audio_event_dogbark",
                    {
                        "begin_timestamp": self.raw_detection_begin_timestamp,
                        "end_timestamp": self.raw_detection_end_timestamp,
                    },
                )

                evt_mgr.queue_event(
                    "dog_bark_end",
                    {
                        "end_timestamp": self.raw_detection_end_timestamp,
                    },
                )

                self.last_raw_bark_end_timestamp = None
                self.raw_detection_begin_timestamp = None
                self.raw_detection_end_timestamp = None
