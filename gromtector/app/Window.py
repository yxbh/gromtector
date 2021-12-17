
import pygame as pg


class Window:
    window_surface: pg.Surface = None

    def __init__(self, title, width=None, height=None):
        width = width if width else 500
        height = height if height else 500

        pg.init()
        logo_img = pg.image.load("gromtector/app/assets/logo.jpg")
        pg.display.set_icon(logo_img)
        pg.display.set_caption(title)

        self.window_surface = pg.display.set_mode((width, height))
