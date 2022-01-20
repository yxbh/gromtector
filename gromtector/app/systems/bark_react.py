from __future__ import annotations
import logging
import queue
import random
import smtplib
from socket import gethostname
import threading
import time
from typing import Sequence

from .BaseSystem import BaseSystem

from pydub import AudioSegment
from simpleaudio import play_buffer
from simpleaudio.shiny import PlayObject


logger = logging.getLogger(__name__)


class BarkReactSystem(BaseSystem):
    bark_response_playback_paths: Sequence[str] = None
    clips: Sequence[AudioSegment] = None
    play_obj: PlayObject = None

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

        self.bark_response_playback_paths = configs["--bark-response-audio"]
        self.bark_notify_email = configs["--bark-notify-email"]
        self.gmail_app_pw = configs["--gmail-app-pw"]

        if self.gmail_app_pw and not self.bark_notify_email:
            err_msg = "An email password was given but no sender email was provided."
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        if not self.gmail_app_pw and self.bark_notify_email:
            err_msg = "An email address was given but no password was provided."
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        self.clips = []
        if self.bark_response_playback_paths:
            for bark_response_playback_path in self.bark_response_playback_paths:
                self.clips.append(AudioSegment.from_file(bark_response_playback_path))
        else:
            logger.warning("No dog bark response audio clips were provided.")

        if self.clips:
            for clip in self.clips:
                clip.apply_gain(+20.0)

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
        if self.play_obj is None and self.clips:
            clip_idx = random.randint(0, len(self.clips)-1)
            clip = self.clips[clip_idx]
            self.play_obj = play_buffer(
                clip.raw_data,
                num_channels=clip.channels,
                bytes_per_sample=clip.sample_width,
                sample_rate=clip.frame_rate,
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
            server_ssl.ehlo()  # optional, called by login()
            server_ssl.login(system.bark_notify_email, system.gmail_app_pw)

            while not system.dogbark_events.empty():
                event = system.dogbark_events.get()

                email_subject = "Gromtector: barking detected"
                email_from = system.bark_notify_email
                email_to = system.bark_notify_email
                email_msg = (
                    "From: {}\n"
                    "To: {}\n"
                    "Subject: {}\n\n"
                    "Barking detected on {}.\n"
                    "{} -\n{}\n\n"
                    "Trigger classes:\n"
                    "{}"
                ).format(
                    email_from,
                    email_to,
                    email_subject,
                    gethostname(),
                    event["begin_timestamp"].astimezone(tz=None),
                    event["end_timestamp"].astimezone(tz=None),
                    "\n".join(
                        [
                            f'"{cl["label"]}": {cl["score"]}'
                            for cl in event["trigger_classes"]
                        ]
                    ),
                )
                # ssl server doesn't support or need tls, so don't call server_ssl.starttls()
                server_ssl.sendmail(email_from, [email_to], email_msg)

            # server_ssl.quit()
            server_ssl.close()

        logger.debug("Reaching the end of the email sender thread.")
