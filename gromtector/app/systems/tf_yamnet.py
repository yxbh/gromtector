from __future__ import annotations
from datetime import datetime
import logging
import threading
import time
import zipfile
from typing import Sequence
import numpy as np
import tensorflow as tf
import audiosegment as ad
from sklearn.preprocessing import minmax_scale

from .BaseSystem import BaseSystem


logger = logging.getLogger(__name__)


class BaseTfYamnetSystem(BaseSystem):
    audio_sample_width: int = 2
    model_path: str = None
    model: tf.lite.Interpreter = None
    model_sample_rate: int = 16000  # The model required audio sample rate.
    model_labels: Sequence[str] = None
    raw_audio_buffer = b""
    raw_audio_utc_begin: datetime = None

    running: bool = False
    inference_thread: threading.Thread = None

    sleep: bool = True
    inference_max_fps: float = 10.0

    def shutdown(self):
        self.running = False
        if self.inference_thread is not None:
            self.inference_thread.join()

    def run(self):
        self.inference_thread = threading.Thread(
            target=self.__class__.run_inference_thread, args=(self,)
        )
        self.inference_thread.start()

    def _recv_audio_data(self, event_type, audio_event) -> None:
        self.raw_audio_utc_begin = audio_event.begin_timestamp

        audio_seg = ad.from_numpy_array(audio_event.data, framerate=audio_event.rate)

        # resample the audio to rate needed by the model.
        resampled_audio_seg = audio_seg.resample(
            sample_rate_Hz=16000, sample_width=self.audio_sample_width, channels=1
        )
        if self.raw_audio_buffer is None:
            self.raw_audio_buffer = resampled_audio_seg.seg.raw_data
        else:
            temp = self.raw_audio_buffer + resampled_audio_seg.seg.raw_data
            self.raw_audio_buffer = temp[
                -self.model_sample_rate * self.audio_sample_width :
            ]  # Only keep the most recent second of audio.


class TfYamnetLiteSystem(BaseTfYamnetSystem):
    """
    Reference: https://tfhub.dev/google/lite-model/yamnet/classification/tflite/1
    """

    def init(self):
        self.model_path = self.get_config().get("--tf-model", "model/")
        logger.debug('Tensorflow model: "{}"'.format(self.model_path))
        logger.debug("Loading model...")
        self.model = tf.lite.Interpreter(self.model_path)
        logger.debug("Loading model... DONE")

        logger.debug("Loading model labels...")
        labels_file = zipfile.ZipFile(self.model_path).open("yamnet_label_list.txt")
        self.model_labels = [l.decode("utf-8").strip() for l in labels_file.readlines()]
        logger.debug("Loading model labels... DONE")

        logger.debug("Setting model stuff up...")
        interpreter = self.model
        self.input_details = interpreter.get_input_details()
        self.waveform_input_index = self.input_details[0]["index"]
        self.output_details = interpreter.get_output_details()
        self.scores_output_index = self.output_details[0]["index"]
        interpreter.allocate_tensors()
        logger.debug("Setting model stuff up... DONE")

        self.get_event_manager().add_listener("new_audio_data", self._recv_audio_data)

        self.running = True

    @classmethod
    def run_inference_thread(cls, system: TfYamnetLiteSystem):
        while system.running:
            if not system.model or not system.model_labels:
                logger.warning("Model not ready.")
                continue

            if not system.raw_audio_buffer:
                continue

            interpreter = system.model

            pcm_int16 = np.frombuffer(system.raw_audio_buffer, dtype=np.int16)
            num_samples = int(0.975 * system.model_sample_rate)
            num_to_pad = num_samples - pcm_int16.size
            if num_to_pad < 0:
                num_to_pad = 0
            num_to_pad += 2
            waveform = np.pad(pcm_int16, (0, num_to_pad))
            int16_iinfo = np.iinfo(np.int16)
            waveform[-1] = int16_iinfo.max
            waveform[-2] = int16_iinfo.min

            waveform = waveform.astype(np.float32)
            waveform = minmax_scale(waveform, feature_range=(-1, 1), copy=False)
            waveform = waveform[:num_samples]

            # interpreter.resize_tensor_input(
            #     system.waveform_input_index, [waveform.size], strict=True
            # )
            # interpreter.allocate_tensors()
            interpreter.set_tensor(system.waveform_input_index, waveform)
            start = time.time()
            interpreter.invoke()
            scores = interpreter.get_tensor(system.scores_output_index)
            end = time.time()

            top_class_index = scores.argmax()
            top_results = tf.math.top_k(scores, k=10)
            top_class_indices = top_results.indices[0].numpy()
            top_class_probs = top_results.values[0].numpy()
            # logger.debug("Detected: {}".format(system.model_labels[top_class_index]))
            # logger.debug(
            #     "Detected (took {:.3f}s): {}".format(
            #         (end - start),
            #         ", ".join(
            #             [
            #                 "{} ({:.3f})".format(
            #                     system.model_labels[idx], scores[0][idx]
            #                 )
            #                 for idx in top_class_indices
            #             ]
            #         ),
            #     )
            # )
            system.get_event_manager().queue_event(
                "detected_classes",
                {
                    "begin_timestamp": system.raw_audio_utc_begin,
                    "classes": [
                        {
                            "label": system.model_labels[idx],
                            "score": scores[0][idx],
                        }
                        for idx in top_class_indices
                    ],
                },
            )

        logger.debug("Reaching the end of the model inference thread.")


class TfYamnetSavedmodelSystem(BaseTfYamnetSystem):
    def init(self) -> None:
        self.model_path = self.get_config().get("--tf-model", "model/")
        logger.debug('Tensorflow model: "{}"'.format(self.model_path))
        logger.debug("Loading model...")
        self.model = tf.saved_model.load(self.model_path)
        logger.debug("Loading model... DONE")

        def class_names_from_csv(class_map_csv_text):
            """Returns list of class names corresponding to score vector."""
            import csv
            import io

            class_map_csv = io.StringIO(class_map_csv_text)
            class_names = [
                display_name
                for (class_index, mid, display_name) in csv.reader(class_map_csv)
            ]
            class_names = class_names[1:]  # Skip CSV header
            return class_names

        class_map_path = self.model.class_map_path().numpy()
        self.model_labels = class_names_from_csv(
            tf.io.read_file(class_map_path).numpy().decode("utf-8")
        )

        self.get_event_manager().add_listener("new_audio_data", self._recv_audio_data)

        self.running = True

    @classmethod
    def run_inference_thread(cls, system: TfYamnetSavedmodelSystem):
        last_time = time.time()
        cumu_time_s = 0.
        while system.running:

            now_time = time.time()
            target_time_per_frame_s = 1.0 / system.inference_max_fps
            frame_time_so_far_s = now_time - last_time
            cumu_time_s += frame_time_so_far_s
            last_time = now_time
            if cumu_time_s < target_time_per_frame_s and system.sleep:
                time.sleep(target_time_per_frame_s - cumu_time_s)
                continue
            else:
                cumu_time_s -= target_time_per_frame_s

            if not system.model or not system.model_labels:
                logger.warning("Model not ready.")
                continue

            if not system.raw_audio_buffer:
                continue

            pcm_int16 = np.frombuffer(system.raw_audio_buffer, dtype=np.int16)
            num_samples = int(0.975 * system.model_sample_rate)

            # Pad the waveform to the model required sample length + 2 so we can
            # add the integer min and max to make sure scaling is relative to the
            # the type min/max.
            num_to_pad = num_samples - pcm_int16.size
            if num_to_pad < 0:
                num_to_pad = 0
            num_to_pad += 2
            waveform = np.pad(pcm_int16, (0, num_to_pad))
            int16_iinfo = np.iinfo(np.int16)
            waveform[-1] = int16_iinfo.max
            waveform[-2] = int16_iinfo.min

            waveform = waveform.astype(np.float32)
            waveform = minmax_scale(waveform, feature_range=(-1, 1), copy=False)
            waveform = waveform[:-2]

            # Run the model, check the output.
            start = time.time()
            scores, embeddings, log_mel_spectrogram = system.model(waveform)
            end = time.time()
            scores.shape.assert_is_compatible_with([None, 521])
            embeddings.shape.assert_is_compatible_with([None, 1024])
            log_mel_spectrogram.shape.assert_is_compatible_with([None, 64])
            scores_max = tf.reduce_max(scores, axis=0)

            top_results = tf.math.top_k(scores_max, k=10)
            top_class_indices = top_results.indices.numpy()
            top_class_probs = top_results.values.numpy()
            # logger.debug("Detected: {}".format(system.model_labels[top_class_index]))
            # logger.debug(
            #     "Detected (took {:.3f}s): {}".format(
            #         (end - start),
            #         ", ".join(
            #             [
            #                 "{} ({:.3f})".format(
            #                     system.model_labels[idx], scores_max[idx]
            #                 )
            #                 for idx in top_class_indices
            #             ]
            #         ),
            #     )
            # )
            system.get_event_manager().queue_event(
                "detected_classes",
                {
                    "begin_timestamp": system.raw_audio_utc_begin,
                    "classes": [
                        {
                            "label": system.model_labels[idx],
                            "score": scores_max[idx],
                        }
                        for idx in top_class_indices
                    ],
                },
            )


class TfYamnetSystem(BaseSystem):
    """
    A wrapper system that determines which Yamnet system to load base on configs.
    """

    _system: BaseSystem = None

    def init(self) -> None:
        model_path = self.get_config()["--tf-model"]
        if model_path.endswith("tflite"):
            self._system = TfYamnetLiteSystem(
                app=self.get_app(), config=self.get_config()
            )
        else:
            self._system = TfYamnetSavedmodelSystem(
                app=self.get_app(), config=self.get_config()
            )
        return self._system.init()

    def shutdown(self) -> None:
        self._system.shutdown()

    def recv_audio_data(self, event_type, audio_event) -> None:
        audio_seg = ad.from_numpy_array(audio_event.data, framerate=audio_event.rate)

        # resample the audio to rate needed by the model.
        resampled_audio_seg = audio_seg.resample(
            sample_rate_Hz=16000, sample_width=2, channels=1
        )
        if self.raw_audio_buffer is None:
            self.raw_audio_buffer = resampled_audio_seg.seg.raw_data
        else:
            temp = self.raw_audio_buffer + resampled_audio_seg.seg.raw_data
            self.raw_audio_buffer = temp[-self.model_sample_rate :]

    def run(self) -> None:
        self._system.run()
