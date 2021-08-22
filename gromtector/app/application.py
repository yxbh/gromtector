from collections import defaultdict
import logging
import queue
import pygame as pg

from .BaseApplication import BaseApplication
from .event_manager import EventManager


logger = logging.getLogger(__name__)


APP_SINGLETON = None


class Application(BaseApplication):
    def __init__(self, args, system_classes=[]):
        global APP_SINGLETON
        if APP_SINGLETON is not None:
            raise RuntimeError(
                "There's already an instance of {} running.".format(self.__class__)
            )
        APP_SINGLETON = self
        
        self.args = args

        pg.init()
        logo_img = pg.image.load("gromtector/app/assets/logo.jpg")
        pg.display.set_icon(logo_img)
        pg.display.set_caption("GROMTECTOR")

        self.screen = pg.display.set_mode((500, 500))
        self.running = True

        self.clock = pg.time.Clock()
        self.max_fps = 100

        self.event_manager = EventManager()

        self.systems = []
        self.system_classes = system_classes

    def init_systems(self):
        for cls in self.system_classes:
            new_sys = cls(self)
            new_sys.init()
            self.systems.append(new_sys)

    def start_systems(self):
        for sys in self.systems:
            sys.run()

    def shutdown_systems(self):
        for sys in self.systems:
            sys.shutdown()

    def update_systems(self, elapsed_time_ms: int):
        for sys in self.systems:
            sys.update(elapsed_time_ms)

    def run(self):
        """
        Main application loop.
        """
        self.init_systems()
        self.start_systems()

        elapsed_time_ms = 0
        while self.running:
            for pg_event in pg.event.get(pump=True):
                if pg_event.type == pg.QUIT:
                    logger.info("Exit requested.")
                    self.running = False

            self.event_manager.dispatch_queued_events()
            self.update_systems(elapsed_time_ms)
            self.event_manager.dispatch_queued_events()
            elapsed_time_ms = self.clock.tick(self.max_fps)

        self.shutdown_systems()

        pg.quit()

    def get_event_manager(self) -> EventManager:
        return self.event_manager
