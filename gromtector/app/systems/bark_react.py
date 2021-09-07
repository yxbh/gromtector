from __future__ import annotations
import logging
import queue
import smtplib
import threading
import time

from .BaseSystem import BaseSystem

from pydub import AudioSegment
from simpleaudio import play_buffer


logger = logging.getLogger(__name__)


class BarkReactSystem(BaseSystem):
    bark_response_playback_path: str = None
    clip = None
    play_obj = None

    dogbark_events: queue.Queue = None

    bark_notify_email: str = None
    gmail_app_pw: str = None
    email_thread: threading.Thread = None

    running: bool = False

    def init(self) -> None:
        evt_mgr = self.get_event_manager()
        evt_mgr.add_listener("dog_bark_begin", self.handle_dogbark_begin)
        evt_mgr.add_listener("audio_event_dogbark", self.handle_dogbark_detected)

        configs = self.get_config()

        self.bark_response_playback_path = configs["--bark-response-audio"]
        self.bark_notify_email = configs["--bark-notify-email"]
        self.gmail_app_pw = configs["--gmail-app-pw"]

        if self.bark_response_playback_path:
            self.clip = AudioSegment.from_file(self.bark_response_playback_path)
        else:
            self.clip = AudioSegment.from_file("samples/voice_clip_goodboy.m4a")
        if self.clip is not None:
            self.clip.apply_gain(+20.0)

        self.dogbark_events = queue.Queue()
        self.running = True

    def run(self):
        self.email_thread = threading.Thread(
            target=self.__class__.run_email_thread, args=(self,)
        )
        self.email_thread.start()

    def shutdown(self):
        self.running = False
        if self.email_thread is not None:
            self.email_thread.join()

    def handle_dogbark_begin(self, event_type, event) -> None:
        if self.play_obj is None:
            self.play_obj = play_buffer(
                self.clip.raw_data,
                num_channels=self.clip.channels,
                bytes_per_sample=self.clip.sample_width,
                sample_rate=self.clip.frame_rate,
            )

    def handle_dogbark_detected(self, event_type, event) -> None:
        if self.bark_notify_email and self.gmail_app_pw:
            self.dogbark_events.put(event)

    def update(self, elapsed_time_ms: int) -> None:
        if self.play_obj is not None and not self.play_obj.is_playing():
            self.play_obj = None

    @classmethod
    def run_email_thread(cls, system: BarkReactSystem) -> None:
        while system.running:
            if system.dogbark_events.empty():
                time.sleep(1)
                continue

            server_ssl = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server_ssl.ehlo() # optional, called by login()
            server_ssl.login(system.bark_notify_email, system.gmail_app_pw)

            while not system.dogbark_events.empty():
                event = system.dogbark_events.get()

                email_subject = "Gromtector: Gromit barking detected"
                email_from = system.bark_notify_email
                email_to = system.bark_notify_email
                email_msg = "From: {}\nTo: {}\nSubject: {}\n\nGromit barking detected: {} - {}\n\nTrigger classes:\n{}".format(
                    email_from,
                    email_to,
                    email_subject,
                    event["begin_timestamp"].astimezone(tz=None),
                    event["end_timestamp"].astimezone(tz=None),
                    "\n".join([f'"{cl["label"]}": {cl["score"]}' for cl in event["trigger_classes"]]),
                )
                # ssl server doesn't support or need tls, so don't call server_ssl.starttls() 
                server_ssl.sendmail(email_from, [email_to], email_msg)

            #server_ssl.quit()
            server_ssl.close()

        logger.debug("Reaching the end of the email sender thread.")

        