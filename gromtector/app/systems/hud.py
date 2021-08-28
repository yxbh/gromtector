from typing import Sequence
from .BaseSystem import BaseSystem
import pygame as pg
import pygame.freetype as pgft


def blit_text(surface, text, pos, font: pgft.Font, fgcolor=pg.Color("black")):
    words = [
        word.split(" ") for word in text.splitlines()
    ]  # 2D array where each row is a list of words.
    space_surface, space_rect = font.render(" ")
    space = space_rect.width
    # space = font.size(" ")[0]  # The width of a space.
    max_width, max_height = surface.get_size()
    x, y = pos
    for line in words:
        for word in line:
            word_surface, word_rect = font.render(word, fgcolor=fgcolor)
            # word_width, word_height = word_surface.get_size()
            word_width = word_rect.width
            word_height = word_rect.height
            if x + word_width >= max_width:
                x = pos[0]  # Reset the x.
                y += word_height  # Start on new row.
            surface.blit(word_surface, (x, y))
            x += word_width + space
        x = pos[0]  # Reset the x.
        y += word_height  # Start on new row.


class HudSystem(BaseSystem):
    font: pgft.SysFont = None
    app_fps: float = 0.0
    spectrum_shape = None
    frequencies_shape = None
    times_shape = None
    times_max: float = 0.0
    times_min: float = 0.0
    sample_rate: int = 0
    detected_classes: Sequence = []
    score_thredshold: float = 0.05

    def init(self):
        self.font = pgft.SysFont(pgft.get_default_font(), size=12)

        evt_mgr = self.get_event_manager()
        evt_mgr.add_listener("new_audio_data", self.receive_audio_data)
        evt_mgr.add_listener("new_app_fps", self.receive_app_fps)
        evt_mgr.add_listener("new_spectrogram_info", self.receive_spec_info)
        evt_mgr.add_listener("detected_classes", self.recev_detected_classes)

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

    def recev_detected_classes(self, event_type, detected_classes):
        detected_classes = [
            dc for dc in detected_classes if dc["score"] > self.score_thredshold
        ]
        detected_classes = sorted(
            detected_classes, key=lambda dc: dc["score"], reverse=True
        )
        self.detected_classes = detected_classes

    def update(self, elapsed_time_ms: int) -> None:
        render_surface = self.get_app().window.window_surface
        txt_color = (0xFF, 0xFF, 0xFF)
        offset_margin = 4

        fps_surface, fps_rect = self.font.render(
            "FPS: {:.2f}".format(self.app_fps), fgcolor=txt_color
        )
        render_surface.blit(fps_surface, (0, 0))

        y_offset = 10 + offset_margin

        sample_rate_surface, sample_rate_rect = self.font.render(
            "ORIGINAL SAMPLE RATE: {}".format(self.sample_rate), fgcolor=txt_color
        )
        render_surface.blit(sample_rate_surface, (0, y_offset))

        y_offset += sample_rate_rect.height + offset_margin

        shapes_txt_surface, shapes_txt_rect = self.font.render(
            "SHAPES: Spectrum{}, Frequencies{}, Times{}".format(
                self.spectrum_shape, self.frequencies_shape, self.times_shape
            ),
            fgcolor=txt_color,
        )
        render_surface.blit(shapes_txt_surface, (0, y_offset))

        y_offset += shapes_txt_rect.height + offset_margin

        time_txt_surface, time_txt_rect = self.font.render(
            "MAX TIME: {:.5f}, MIN TIME: {:.5f}".format(self.times_max, self.times_min),
            fgcolor=txt_color,
        )
        render_surface.blit(time_txt_surface, (0, y_offset))

        y_offset += time_txt_rect.height + offset_margin

        detected_classes_txt = "DETECTED:\n" + "\n".join(
            [
                "{} ({:.3f})".format(dcls["label"], dcls["score"])
                for dcls in self.detected_classes
            ]
        )
        blit_text(
            render_surface,
            detected_classes_txt,
            (0, y_offset),
            self.font,
            fgcolor=txt_color,
        )

        # classes_surface, classes_rect = self.font.render(
        #     "DETECTED:\n"
        #     + "\n".join(
        #         [
        #             "{} ({})".format(dcls["label"], dcls["score"])
        #             for dcls in self.detected_classes
        #         ]
        #     ),
        #     fgcolor=txt_color,
        # )
        # render_surface.blit(classes_surface, (0, y_offset))
