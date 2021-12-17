from typing import Mapping, Sequence
from gromtector.app.systems.BaseSystem import BaseSystem
import logging
import pygame as pg

from .BaseApplication import BaseApplication
from .EventManager import EventManager
from .Window import Window


logger = logging.getLogger(__name__)


APP_SINGLETON = None


class Application(BaseApplication):
    def __init__(self, args: Mapping, system_classes: Sequence[BaseSystem] = []):
        global APP_SINGLETON
        if APP_SINGLETON is not None:
            raise RuntimeError(
                "There's already an instance of {} running.".format(self.__class__)
            )
        APP_SINGLETON = self

        self.args = args

        self._is_server = args["--server-mode"]
        self._is_client = args["--client-mode"]

        self.window = Window(
            title="GROMTECTOR: Server" if self.is_server else "GROMTECTOR: Client",
            width=900,
            height=400,
        )
        self.running: bool = True

        self.clock = pg.time.Clock()
        self.max_fps = int(self.args.get("--max-fps", 60))

        self.event_manager = EventManager()

        self.systems: Sequence[BaseSystem] = []
        self.system_classes: Sequence[BaseSystem.__class__] = system_classes

    @property
    def is_server(self) -> bool:
        return self._is_server

    @property
    def is_client(self) -> bool:
        return self._is_client

    def init_systems(self):
        for cls in self.system_classes:
            new_sys = cls(self, config=self.args)
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

    def update(self, elapsed_time_ms: int):
        self.event_manager.queue_event("new_app_fps", self.clock.get_fps())

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
                elif pg_event.type in [
                    pg.KEYDOWN,
                    pg.KEYUP,
                ]:
                    self.event_manager.dispatch_event("keyboard_event", pg_event)

            self.window.window_surface.fill((0, 0, 0))

            self.event_manager.dispatch_queued_events()
            self.update(elapsed_time_ms)
            self.update_systems(elapsed_time_ms)
            self.event_manager.dispatch_queued_events()
            elapsed_time_ms = self.clock.tick(self.max_fps)

            pg.display.flip()

        self.shutdown_systems()

    def get_event_manager(self) -> EventManager:
        return self.event_manager
