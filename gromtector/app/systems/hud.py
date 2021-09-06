from datetime import datetime
from typing import Sequence, Tuple
from .BaseSystem import BaseSystem
import pygame as pg
import pygame.freetype as pgft


def blit_text(
    surface: pg.Surface, text: str, pos: Tuple[int, int], font: pgft.Font
) -> pg.Rect:
    words = [
        word.split(" ") for word in text.splitlines()
    ]  # 2D array where each row is a list of words.
    space_surface, space_rect = font.render(" ")
    space = space_rect.width
    # space = font.size(" ")[0]  # The width of a space.
    max_width, max_height = surface.get_size()
    x, y = pos
    text_surface_width = 0
    for line in words:
        for word in line:
            word_surface, word_rect = font.render(word)
            # word_width, word_height = word_surface.get_size()
            word_width = word_rect.width
            word_height = word_rect.height
            if x + word_width >= max_width:
                x = pos[0]  # Reset the x.
                y += word_height  # Start on new row.
            surface.blit(word_surface, (x, y))
            x += word_width + space
        text_surface_width = max(x, text_surface_width)
        x = pos[0]  # Reset the x.
        y += word_height  # Start on new row.
        y += 1  # TODO: temp padding for testing.

    return pg.Rect(pos, (text_surface_width, y))


class HudSystem(BaseSystem):
    font: pgft.SysFont = None
    default_font_size: int = 12
    dog_audio_status_font = None

    app_fps: float = 0.0
    spectrum_shape = None
    frequencies_shape = None
    times_shape = None
    times_max: float = 0.0
    times_min: float = 0.0
    sample_rate: int = 0

    detected_classes: Sequence = []
    score_thredshold: float = 0.05

    dog_audio_active: bool = False
    latest_event_dogbark_begin: datetime = None
    latest_event_dogbark_end: datetime = None

    last_trigger_classes: Sequence = None  # classes that triggered the dog/bark detected event.

    def init(self):
        self.last_trigger_classes = []

        txt_color = (0xFF, 0xFF, 0xFF)
        self.font = pgft.SysFont(pgft.get_default_font(), size=self.default_font_size)
        self.font.fgcolor = txt_color
        self.dog_audio_status_font = pgft.SysFont(
            pgft.get_default_font(), size=self.default_font_size + 3, bold=True
        )
        self.dog_audio_status_font.fgcolor = txt_color
        self.dog_audio_status_font.pad = True

        evt_mgr = self.get_event_manager()
        evt_mgr.add_listener("new_audio_data", self.receive_audio_data)
        evt_mgr.add_listener("new_app_fps", self.receive_app_fps)
        evt_mgr.add_listener("new_spectrogram_info", self.receive_spec_info)
        evt_mgr.add_listener("detected_classes", self.recev_detected_classes)
        evt_mgr.add_listener("dog_bark_begin", self.recv_dog_bark_detected)
        evt_mgr.add_listener("dog_bark_end", self.recv_dog_bark_detected)
        evt_mgr.add_listener("audio_event_dogbark", self.recv_highlvl_audio_evt)

    def receive_app_fps(self, event_type, event):
        self.app_fps = event

    def receive_spec_info(self, event_type, event):
        self.spectrum_shape = event["new_spectrum_shape"]
        self.frequencies_shape = event["new_frequencies_shape"]
        self.times_shape = event["new_times_shape"]
        self.times_max = event["new_max_time"]
        self.times_min = event["new_min_time"]

    def receive_audio_data(self, event_type, new_audio_data):
        self.sample_rate = new_audio_data.rate

    def recev_detected_classes(self, event_type, event):
        detected_classes = event["classes"]
        detected_classes = [
            dc for dc in detected_classes if dc["score"] > self.score_thredshold
        ]
        detected_classes = sorted(
            detected_classes, key=lambda dc: dc["score"], reverse=True
        )
        self.detected_classes = detected_classes

    def recv_dog_bark_detected(self, event_type, evt):
        self.dog_audio_active = event_type == "dog_bark_begin"
        if event_type == "dog_bark_begin":
            self.last_trigger_classes = evt["detected_classes"]

    def recv_highlvl_audio_evt(self, event_type, evt: dict):
        if event_type == "audio_event_dogbark":
            self.latest_event_dogbark_begin = evt["begin_timestamp"]
            self.latest_event_dogbark_end = evt["end_timestamp"]

    def update(self, elapsed_time_ms: int) -> None:
        render_surface = self.get_app().window.window_surface
        offset_margin = 4

        fps_rect = self.font.render_to(
            surf=render_surface,
            dest=(0, 0),
            text="FPS: {:.2f}  ORIGINAL SAMPLE RATE: {}".format(
                self.app_fps, self.sample_rate
            ),
        )

        y_offset = 10 + offset_margin
        # y_offset = fps_rect.height + offset_margin
        shapes_txt_rect = self.font.render_to(
            surf=render_surface,
            dest=(0, y_offset),
            text="SHAPES: Spectrum{}, Frequencies{}, Times{}, MAX TIME: {:.5f}, MIN TIME: {:.5f}".format(
                self.spectrum_shape,
                self.frequencies_shape,
                self.times_shape,
                self.times_max,
                self.times_min,
            ),
        )

        y_offset += shapes_txt_rect.height + offset_margin
        detected_classes_txt = "TOP DETECTED:\n" + "\n".join(
            [
                "{} ({:.3f})".format(dcls["label"], dcls["score"])
                for dcls in self.detected_classes
            ]
        )
        detected_clses_rect = blit_text(
            render_surface,
            detected_classes_txt,
            (0, y_offset),
            self.font,
        )

        x_offset = 130
        if self.dog_audio_active:
            dog_aud_rect = self.dog_audio_status_font.render_to(
                surf=render_surface,
                dest=(x_offset, y_offset),
                text="DOG AUDIO ACTIVE".format(self.times_max, self.times_min),
                bgcolor="red",
            )
        else:
            dog_aud_rect = self.dog_audio_status_font.render_to(
                surf=render_surface,
                dest=(x_offset, y_offset),
                text="DOG AUDIO INACTIVE".format(self.times_max, self.times_min),
                bgcolor="dark green",
            )

        # dog_aud_rect.y += dog_aud_rect.height + offset_margin
        if self.latest_event_dogbark_begin and self.latest_event_dogbark_end:
            trigger_classes_txt = ""
            if self.last_trigger_classes:
                trigger_classes_txt = "Trigger classes:\n" + "\n".join(
                    [
                        "{} ({:.3f})".format(dcls["label"], dcls["score"])
                        for dcls in self.last_trigger_classes
                    ]
                )

            # DT_FORMAT =
            blit_text(
                render_surface,
                "LAST:\n{}\n{}\n{}".format(
                    self.latest_event_dogbark_begin.astimezone(tz=None),
                    self.latest_event_dogbark_end.astimezone(tz=None),
                    trigger_classes_txt,
                ),
                (dog_aud_rect.left + 200, dog_aud_rect.top),
                self.font,
            )
