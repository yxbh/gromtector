from .BaseSystem import BaseSystem
import pygame as pg
import pygame.freetype as pgft


class HudSystem(BaseSystem):
    font: pgft.SysFont = None
    app_fps = None
    spectrum_shape = None
    frequencies_shape = None
    times_shape = None
    times_max = None

    def init(self):
        self.font = pgft.SysFont(pgft.get_default_font(), size=12)

        self.get_event_manager().add_listener("new_app_fps", self.receive_app_fps)
        self.get_event_manager().add_listener(
            "new_spectrogram_info", self.receive_spec_info
        )

    def receive_app_fps(self, event_type, event):
        self.app_fps = event

    def receive_spec_info(self, event_type, event):
        self.spectrum_shape = event["new_spectrum_shape"]
        self.frequencies_shape = event["new_frequencies_shape"]
        self.times_shape = event["new_times_shape"]
        self.times_max = event["new_max_time"]

    def update(self, elapsed_time_ms: int) -> None:
        render_surface = self.get_app().window.window_surface
        txt_color = (0xFF, 0xFF, 0xFF)

        fps_surface, fps_rect = self.font.render(
            "FPS: {}".format(self.app_fps), fgcolor=txt_color
        )
        render_surface.blit(fps_surface, (0, 0))

        y_offset = 10

        shapes_txt_surface, shapes_txt_rect = self.font.render(
            "SHAPES: Spectrum{}, Frequencies{}, Times{}".format(
                self.spectrum_shape, self.frequencies_shape, self.times_shape
            ),
            fgcolor=txt_color,
        )
        render_surface.blit(shapes_txt_surface, (0, y_offset))

        y_offset += shapes_txt_rect.height

        time_txt_surface, time_txt_rect = self.font.render(
            "MAX TIME: {}".format(self.times_max),
            fgcolor=txt_color,
        )
        render_surface.blit(time_txt_surface, (0, y_offset))
