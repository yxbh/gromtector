import numpy as np
import pygame as pg
import matplotlib.cm as mplcm

from .BaseSystem import BaseSystem


class SpectrogramGraphSystem(BaseSystem):
    Sxx = None
    freqs = None
    times = None
    palette = [(max((x - 128) * 2, 0), x, min(x * 2, 255)) for x in range(256)]

    def init(self):
        configs = self.get_config()
        palette_name = configs.get("--graph-palette", None)
        if palette_name:
            cmap = mplcm.get_cmap(palette_name.lower())
            palette_norm = [cmap(x / 255) for x in range(256)]
            self.palette = [
                (int(r * 255), int(g * 255), int(b * 255)) for (r, g, b, a) in palette_norm
            ]

        self.get_event_manager().add_listener("new_spectrogram", self.recv_spectrogram)

    def recv_spectrogram(self, event_type, spectrogram_data):
        self.Sxx = spectrogram_data["signals"]
        self.freqs = spectrogram_data["frequencies"]
        self.times = spectrogram_data["times"]

    def update(self, elapsed_time_ms: int) -> None:
        if self.Sxx is None:
            return

        self.specgram_surface = pg.Surface(
            (self.Sxx.shape[1], self.Sxx.shape[0]), depth=8
        )
        self.specgram_surface.set_palette(self.palette)

        data = np.rot90(self.Sxx, 3)
        # data = (data - data.min()) / (data.max() - data.min()) * 255  # dynamic min max linearly normalisation.
        min = -60
        max = 60
        data = (data - min) / (max - min) * 255
        np.clip(data, a_min=0, a_max=255, out=data)
        data = data.astype(dtype=np.uint8)

        pg.surfarray.blit_array(self.specgram_surface, data)
        target_surface = pg.transform.scale2x(self.specgram_surface)
        render_surface = self.get_app().window.window_surface
        render_surface.blit(target_surface, (0, 0))
