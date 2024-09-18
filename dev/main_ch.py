import os
import sys
import logging
from uuid import uuid4
from threading import Thread
from queue import Queue
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint
import ankaios_pb2 as ank
from config import ANKAIOS_CONTROL_INTERFACE_BASE_PATH
from logger import get_logger

# pylint: disable=no-member

logger: logging.Logger = get_logger()


class Ankaios:
    """
    Class for interacting with the Ankaios server

    This class access the FIFO files of the Ankaios control interface.
    Hence only one object of this class should be created.
    """

    def __init__(self):
        """
        Creates a new Ankaios object to interact with the control interface
        :param logger: The logger to object should use for logging
        :type logger : logging.Logger
        """
        self._response_queues = {}
        self._read_messages_thread = Thread(target=self._read_messages, daemon=True)
        self._read_messages_thread.start()

        if not os.path.exists(
            f"{ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input"
        ) or not os.path.exists(f"{ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output"):
            logger.error("no connection to Ankaios control interface")
            sys.exit(1)

        self._request_queue = Queue()
        self._send_requests_thread = Thread(target=self._send_requests, daemon=True)
        self._send_requests_thread.start()
        logger.debug("Created object of %s", str(self.__class__.__name__))

    def __del__(self) -> None:
        logger.debug("Destroyed object of %s", str(self.__class__.__name__))

    def _read_messages(self):
        with open(f"{ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb") as f:

            while True:
                varint_buffer = (
                    b""  # Buffer for reading in the byte size of the proto msg
                )
                while True:
                    next_byte = f.read(1)  # Consume byte for byte
                    if not next_byte:
                        break
                    varint_buffer += next_byte
                    if (
                        next_byte[0] & 0b10000000 == 0
                    ):  # Stop if the most significant bit is 0 (indicating the last byte of the varint)
                        break
                msg_len, _ = _DecodeVarint(
                    varint_buffer, 0
                )  # Decode the varint and receive the proto msg length

                msg_buf = b""  # Buffer for the proto msg itself
                while msg_len > 0:
                    next_bytes = f.read(
                        msg_len
                    )  # Read exact amount of byte according to the calculated proto msg length
                    if not next_bytes:
                        break
                    msg_len -= len(next_bytes)
                    msg_buf += next_bytes

                from_server = ank.FromServer()
                try:
                    from_server.ParseFromString(
                        msg_buf
                    )  # Deserialize the received proto msg
                except Exception as e:
                    logger.debug("Invalid response, parsing error: '%s'", e)
                    continue

                if from_server.response is not None:
                    response = from_server.response
                    request_id = response.requestId
                    response_queue = self._response_queues.get(request_id)
                    if response_queue is not None:
                        del self._response_queues[request_id]
                        response_queue.put(response)
                    else:
                        logger.debug("Response for unknown RequestId: %s", request_id)
                else:
                    logger.debug("Received None as response message: %s", from_server)

    def _send_requests(self):
        with open(f"{ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output", "ab") as f:
            while True:
                request = self._request_queue.get()
                request_byte_len = request.ByteSize()  # Length of the msg
                proto_request = request.SerializeToString()  # Serialized proto msg
                logger.debug("Sending Request: %s\n", request)
                f.write(
                    _VarintBytes(request_byte_len)
                )  # Send the byte length of the proto msg
                f.write(proto_request)  # Send the proto msg itself
                f.flush()

    def get_state(self):
        """
        Get the current Ankaios state
        :returns: the current Ankaios server state
        :rtype: ank.CompleteState
        """
        request_complete_state = ank.Request(
            completeStateRequest=ank.CompleteStateRequest(fieldMask=["workloadStates"]),
        )
        return self._execute_request(request_complete_state).completeState

    def delete_workload(self, workload_name):
        """
        Delete a workload from Ankaios
        :param workload_name: The name of the workload
        :type workload_name : str
        :returns: server response to SetState request
        :rtype: ank.FromServer

        Example
        -------

        ::
            ankaios.delete_workload("nginx")
        """
        update_state_request = ank.Request(
            updateStateRequest=ank.UpdateStateRequest(
                newState=ank.CompleteState(desiredState=ank.State(apiVersion="v0.1")),
                updateMask=[f"desiredState.workloads.{workload_name}"],
            )
        )
        return self._execute_request(update_state_request)

    def add_workload(
        self,
        workload_name,
        agent,
        runtime,
        runtime_config,
        restart_policy,
        tags,
        dependencies,
    ):
        """Creates a new Ankaios workload
        :param workload_name: The name of the workload
        :type workload_name : str
        :param agent: The agent the workload should run on
        :type agent : str
        :param runtime: The runtime to used
        :type runtime_config : str
        :param runtime: The runtime specific configuration
        :type runtime_config : str
        :returns: server response to SetState request
        :rtype: ank.FromServer

        Example
        -------

        ::
            ankaios.add_workload(
                workload_name="nginx",
                agent="agent_A",
                runtime_config=yaml.dump(
                    {
                        "image": "docker.io/library/nginx:latest",
                        "commandOptions": ["--net=host"],
                    }
                ),
            )
        """
        update_state_request = ank.Request(
            updateStateRequest=ank.UpdateStateRequest(
                newState=ank.CompleteState(
                    desiredState=ank.State(
                        apiVersion="v0.1",
                        workloads={
                            workload_name: ank.Workload(
                                agent=agent,
                                runtime=runtime,
                                runtimeConfig=runtime_config,
                                tags=[
                                    ank.Tag(key=key, value=value)
                                    for key, value in tags.items()
                                ],
                                dependencies={
                                    name: ank.AddCondition.Value(condition)
                                    for name, condition in dependencies.items()
                                },
                                restartPolicy=ank.RestartPolicy.Value(restart_policy),
                            )
                        },
                    )
                ),
                updateMask=[f"desiredState.workloads.{workload_name}"],
            )
        )
        return self._execute_request(update_state_request)

    def _execute_request(self, request):
        request_id = str(uuid4())
        response_queue = Queue()
        self._response_queues[request_id] = response_queue
        request.requestId = request_id

        to_server = ank.ToServer(request=request)

        self._request_queue.put(to_server)
        return response_queue.get()
