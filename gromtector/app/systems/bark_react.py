from .BaseSystem import BaseSystem

from pydub import AudioSegment
from pydub.playback import play

from simpleaudio import play_buffer


class BarkReactSystem(BaseSystem):
    def init(self) -> None:
        evt_mgr = self.get_event_manager()
        evt_mgr.add_listener("dog_bark_begin", self.handle_dogbark_detected)

        self.clip = AudioSegment.from_file("samples/voice_clip_goodboy.m4a")
        self.play_obj = None

    def handle_dogbark_detected(self, event_type, event) -> None:
        if self.play_obj is None:
            self.play_obj = play_buffer(
                self.clip.raw_data,
                num_channels=self.clip.channels,
                bytes_per_sample=self.clip.sample_width,
                sample_rate=self.clip.frame_rate,
            )

    def update(self, elapsed_time_ms: int) -> None:
        if self.play_obj is not None and not self.play_obj.is_playing():
            self.play_obj = None
