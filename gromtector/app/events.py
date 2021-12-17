from datetime import datetime
from io import BytesIO
from typing import Any, Mapping, Sequence

import numpy as np


class ClientDoorKnockEvent:
    def __init__(self, ip):
        self.event_type = "client_door_knock"
        self.client_ip = ip


class ClientDataCleanupRequestEvent:
    EVENT_TYPE = "ClientDataCleanupRequestEvent"

    def __init__(self, client_id):
        self.event_type = self.__class__.EVENT_TYPE
        self.client_id = client_id


class ClientHeartbeatEvent:
    def __init__(self, ip) -> None:
        self.event_type = "client_heartbeat"
        self.client_local_ip = ip
        self.is_heartbeat = True


class InputAudioDataEvent:
    EVENT_TYPE = "new_audio_data"

    def __init__(self, data, rate: int, begin_timestamp, client_id=0):
        self.client_id = client_id  # default value. It could be any thing.
        self.event_type = self.__class__.EVENT_TYPE
        self.data = data
        self.rate: int = rate
        self.begin_timestamp: datetime = begin_timestamp

    def __getstate__(self) -> Any:
        np_bytes = BytesIO()
        np.save(np_bytes, self.data, allow_pickle=True)
        return {
            "client_id": self.client_id,
            "event_type": self.event_type,
            "data": np_bytes.getvalue(),
            "rate": self.rate,
            "begin_timestamp": self.begin_timestamp,
        }

    def __setstate__(self, blob) -> None:
        load_bytes = BytesIO(blob["data"])
        loaded_np = np.load(load_bytes, allow_pickle=True)
        self.client_id = blob["client_id"]
        self.event_type = blob["event_type"]
        self.data = loaded_np
        self.rate = blob["rate"]
        self.begin_timestamp = blob["begin_timestamp"]


class DetectedObjectClassesEvent:
    EVENT_TYPE = "detected_classes"

    def __init__(
        self, client_id, begin_timestamp: datetime, classes: Sequence[Mapping[str, Any]]
    ):
        self.event_type = self.__class__.EVENT_TYPE
        self.client_id = client_id
        self.begin_timestamp = begin_timestamp
        self.classes = classes


class DogBarkBeganEvent:
    EVENT_TYPE = "dog_bark_begin"

    def __init__(
        self,
        begin_timestamp: datetime,
        detected_classes: Sequence[Mapping[str, Any]],
        dog_class_threshold: float,
        dog_audio_class_threshold: float,
        client_id=0,
    ):
        self.event_type = self.__class__.EVENT_TYPE
        self.client_id = client_id
        self.begin_timestamp = begin_timestamp
        self.detected_classes = detected_classes
        self.dog_class_threshold = dog_class_threshold
        self.dog_audio_class_threshold = dog_audio_class_threshold


class DogBarkEndedEvent:
    EVENT_TYPE = "dog_bark_end"

    def __init__(
        self,
        end_timestamp: datetime,
        client_id=0,
    ):
        self.event_type = self.__class__.EVENT_TYPE
        self.client_id = client_id
        self.end_timestamp = end_timestamp


class AudioEventDogBarkEvent:
    EVENT_TYPE = "audio_event_dogbark"

    def __init__(
        self,
        begin_timestamp: datetime,
        end_timestamp: datetime,
        trigger_classes: Sequence[Mapping[str, Any]],
        dog_class_threshold: float,
        dog_audio_class_threshold: float,
        client_id=0,
    ):
        self.event_type = self.__class__.EVENT_TYPE
        self.client_id = client_id
        self.begin_timestamp = begin_timestamp
        self.end_timestamp = end_timestamp
        self.trigger_classes = trigger_classes
        self.dog_class_threshold = dog_class_threshold
        self.dog_audio_class_threshold = dog_audio_class_threshold
