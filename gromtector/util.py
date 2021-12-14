from time import time


class ElapsedTimer:

    def __init__(self):
        self.init_time = time()
        self.last_time = self.init_time

    def start(self):
        self.init_time = time()
        self.last_time = self.init_time

    def elapsed(self):
        """
        Get the amount of time elapsed since the timer started or the last time
        a measurement was taken.
        """
        new_time = time()
        diff = new_time - self.last_time
        self.last_time = new_time
        return diff


class HeartBeatTimer(ElapsedTimer):
    def __init__(self, heartbeat_interval_s: float):
        self.heartbeat_interval = heartbeat_interval_s
        self.culmu_time = 0.0
        super().__init__()

    @property
    def is_heartbeat(self):
        self.culmu_time += self.elapsed()
        is_heartbeat = False
        if self.culmu_time >= self.heartbeat_interval:
            is_heartbeat = True
            self.culmu_time %= self.heartbeat_interval

        return is_heartbeat
