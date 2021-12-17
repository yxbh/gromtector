from __future__ import annotations
import json
import logging
import pickle
from queue import Queue
import socket
from threading import Thread
import time
from typing import Mapping
import zmq
from zmq.sugar.constants import POLLIN
from gromtector.app.events import (
    AudioEventDogBarkEvent,
    ClientDataCleanupRequestEvent,
    ClientDoorKnockEvent,
    ClientHeartbeatEvent,
    DetectedObjectClassesEvent,
    DogBarkBeganEvent,
    DogBarkEndedEvent,
)

from gromtector.util import ElapsedTimer, HeartBeatTimer

from .BaseSystem import BaseSystem


logger = logging.getLogger(__name__)


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 1))  # connect() for UDP doesn't send packets
    local_ip_address = s.getsockname()[0]
    s.close()
    return local_ip_address


class MqSystem(BaseSystem):
    """
    A message system to support remote server-client model for Gromtector.
    """

    def init(self):
        self.zmq_ctx = zmq.Context()
        self._thread: Thread = None
        self.local_ip = get_local_ip()

        evt_manager = self.get_event_manager()
        if self.app.is_client:
            self.q_p2server = Queue()
            evt_manager.add_listener("push_to_server", self.queue_push_to_server)
            evt_manager.add_listener("new_audio_data", self.queue_push_to_server)

        elif self.app.is_server:
            self.q_b2clients = Queue()
            evt_manager.add_listener(
                "broadcast_to_clients", self.queue_broadcast_to_clients
            )
            evt_manager.add_listener(DogBarkBeganEvent.EVENT_TYPE, self.queue_broadcast_to_clients)
            evt_manager.add_listener(DogBarkEndedEvent.EVENT_TYPE, self.queue_broadcast_to_clients)
            evt_manager.add_listener(AudioEventDogBarkEvent.EVENT_TYPE, self.queue_broadcast_to_clients)
            evt_manager.add_listener(DetectedObjectClassesEvent.EVENT_TYPE, self.queue_broadcast_to_clients)

        self.running = True

    def dispatch_event_locally(self, event):
        """
        Dispatch an externally recevied event internally.
        """
        evt_manager = self.get_event_manager()
        if isinstance(event, Mapping):
            evt_manager.queue_event(event["event_type"], event)
        else:
            evt_manager.queue_event(event.event_type, event)

    def queue_push_to_server(self, evt_type, event):
        # logger.debug('Queue data to push to server: "%s", %s', evt_type, event)

        if evt_type == "broadcast_to_clients":
            data = event
        else:
            data = event
        self.q_p2server.put(data)

    def queue_broadcast_to_clients(self, evt_type, data):
        # logger.debug("Queue data to broadcast to clients: %s", data)
        self.q_b2clients.put(data)

    def shutdown(self):
        self.running = False
        if self._thread:
            self._thread.join()

    def update(self, elapsed_time_ms: int) -> None:
        pass

    def run(self):
        if self.config.get("--server-mode"):
            self._thread = Thread(
                target=self.__class__.run_zmq_server_thread, args=(self,)
            )
            self._thread.start()
        elif self.config.get("--client-mode"):
            self._thread = Thread(
                target=self.__class__.run_zmq_client_thread,
                args=(self, self.config.get("--client-mode")),
            )
            self._thread.start()

    @classmethod
    def run_zmq_server_thread(cls, system: MqSystem):
        logger.debug("Starting MQ server thread...")
        logger.debug("Binding to port...")
        server_socket = system.zmq_ctx.socket(zmq.ROUTER)
        server_socket.bind("tcp://*:19912")

        zmq_clients = {}  # id to last heartbeat time
        event_manager = system.get_event_manager()

        logger.debug("Entering MQ server thread loop...")
        while system.running:
            evt_mask = server_socket.poll(0)
            if evt_mask == POLLIN:
                client_id = server_socket.recv()
                msg = server_socket.recv_pyobj()
                # logger.debug("Server received %s, %s", client_id, msg)

                if client_id not in zmq_clients:
                    logger.debug("zmq client %s joined.", client_id)
                zmq_clients[client_id] = time.time()

                if hasattr(msg, "client_id"):
                    msg.client_id = client_id
                system.dispatch_event_locally(msg)

            elif evt_mask != 0:
                logger.debug("Client received event mask: %s", evt_mask)

            while not system.q_b2clients.empty():
                data2b = system.q_b2clients.get()
                # logger.debug(
                #     "MQ Server sending broadcast to %i clients: %s",
                #     len(zmq_clients),
                #     data2b,
                # )
                if hasattr(data2b, "client_id"):
                    server_socket.send_multipart(
                        [data2b.client_id, pickle.dumps(data2b)]
                    )
                else:
                    for client_id in zmq_clients:
                        server_socket.send_multipart(
                            [client_id, pickle.dumps(data2b)]
                        )

            # socket.send_json({"ack": "ack"})
            # logger.debug("%s received %s", system.__class__, msg)

            zmq_client_timeout_s = 10
            for client_id, last_comm_time in list(zmq_clients.items()):
                if time.time() - last_comm_time >= zmq_client_timeout_s:
                    logger.debug("zmq client %s disconnected.", client_id)
                    event_manager.queue_event(
                        None, ClientDataCleanupRequestEvent(client_id)
                    )
                    zmq_clients.pop(client_id)

        logger.debug("Terminating MQ server thread...")

    @classmethod
    def run_zmq_client_thread(cls, system: MqSystem, server_addr: str):
        logger.debug("Starting MQ client thread...")
        logger.debug("Connecting to server %s...", server_addr)
        client_socket = system.zmq_ctx.socket(zmq.DEALER)
        client_socket.connect(f"tcp://{server_addr}:19912")

        client_socket.send_pyobj(ClientDoorKnockEvent(system.local_ip))

        evt_manager = system.app.get_event_manager()

        heartbeat_timer = HeartBeatTimer(1)
        heartbeat_timer.start()

        logger.debug("Entering MQ client thread loop...")
        while system.running:
            evt_mask = client_socket.poll(0)

            if evt_mask == POLLIN:
                msg = client_socket.recv_pyobj()
                # logger.debug("Client received %s", msg)
                system.dispatch_event_locally(msg)                

            elif evt_mask != 0:
                logger.debug("Client received event mask: %s", evt_mask)

            while not system.q_p2server.empty():
                data2p = system.q_p2server.get()
                # logger.debug("MQ Client sending: %s", data2p)
                client_socket.send_pyobj(data2p)

            if heartbeat_timer.is_heartbeat:
                logger.debug("Sending client heartbeat...")
                client_socket.send_pyobj(ClientHeartbeatEvent(ip=system.local_ip))

            time.sleep(0.01)

        logger.debug("Terminating MQ client thread...")
