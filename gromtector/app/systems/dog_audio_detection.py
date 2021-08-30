from datetime import datetime
from .BaseSystem import BaseSystem


_CLASSES_OF_INTEREST = [
    "Dog",
    "dogs",
    "canidae",
    "Domestic animals",
    "Wild animals",
    "pets",
    "wolves",
    "Animal",
    "Bark",
    "Whimper (dog)",
    "Growling",
    "Howl",
    "Yip",
]

CLASSES_OF_INTEREST = [s.lower() for s in _CLASSES_OF_INTEREST]


class DogAudioDetectionSystem(BaseSystem):
    dog_audio_detected: bool = False
    detection_begin_timestamp: datetime = None
    detection_end_timestamp: datetime = None

    def init(self) -> None:
        evt_mgr = self.get_event_manager()
        evt_mgr.add_listener("detected_classes", self.recv_dclasses)

    def recv_dclasses(self, event_type, event) -> None:

        detected_classes = event["classes"]
        for cls_ in detected_classes:
            cls_lbl = cls_["label"].lower()
            if cls_lbl in CLASSES_OF_INTEREST:
                if not self.dog_audio_detected:
                    self.detection_begin_timestamp = event["begin_timestamp"]
                    self.detection_end_timestamp = None

                self.dog_audio_detected = True
            else:
                if self.dog_audio_detected:
                    self.detection_end_timestamp = datetime.utcnow()
                else:
                    self.detection_begin_timestamp = None

                self.dog_audio_detected = False

    def update(self, elapsed_time_ms: int) -> None:
        evt_mgr = self.get_event_manager()
        if self.dog_audio_detected:
            evt_mgr.queue_event(
                "dog_audio_begin",
                {
                    "begin_timestamp": self.detection_begin_timestamp,
                    "end_timestamp": self.detection_end_timestamp,
                },
            )
        else:
            evt_mgr.queue_event(
                "dog_audio_end",
                {
                    "begin_timestamp": self.detection_begin_timestamp,
                    "end_timestamp": self.detection_end_timestamp,
                },
            )

        if self.detection_begin_timestamp and self.detection_end_timestamp:
            evt_mgr.queue_event(
                "audio_event_dogbark",
                {
                    "begin_timestamp": self.detection_begin_timestamp,
                    "end_timestamp": self.detection_end_timestamp,
                },
            )
