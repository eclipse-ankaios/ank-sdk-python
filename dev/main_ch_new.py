import ankaios_pb2 as ank
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint
from uuid import uuid4
from threading import Thread
from queue import Queue


ANKAIOS_CONTROL_INTERFACE_BASE_PATH = "/run/ankaios/control_interface"


class Ankaios:
    """
    Class for interacting with the Ankaios server

    This class access the FIFO files of the Ankaios control interface.
    Hence only one object of this class should be created.
    """

    def __init__(self, logger):
        """
        Creates a new Ankaios object to interact with the control interface
        :param logger: The logger to object should use for logging
        :type logger : logging.Logger
        """
        self.logger = logger
        self._response_queues = {}
        self._read_messages_thread = Thread(target=self._read_messages, daemon=True)
        self._read_messages_thread.start()

        self._request_queue = Queue()
        self._send_requests_thread = Thread(target=self._send_requests, daemon=True)
        self._send_requests_thread.start()

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
                    self.logger.info(f"Invalid response, parsing error: '{e}'")
                    continue

                if from_server.response is not None:
                    response = from_server.response
                    request_id = response.requestId
                    response_queue = self._response_queues.get(request_id)
                    if response_queue is not None:
                        del self._response_queues[request_id]
                        response_queue.put(response)
                    else:
                        self.logger.info(
                            f"Response for unknown RequestId: {request_id}"
                        )
                else:
                    self.logger.info(
                        f"Received None as response message: {from_server}"
                    )

    def _send_requests(self):
        with open(f"{ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output", "ab") as f:
            while True:
                request = self._request_queue.get()
                request_byte_len = request.ByteSize()  # Length of the msg
                proto_request = request.SerializeToString()  # Serialized proto msg
                self.logger.info(f"Sending Request: {{{request}}}\n")
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
        request_complete_state = request = ank.Request(
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
        update_state_request = request = ank.Request(
            updateStateRequest=ank.UpdateStateRequest(
                newState=ank.CompleteState(desiredState=ank.State(apiVersion="v0.1")),
                updateMask=[f"desiredState.workloads.{workload_name}"],
            )
        )
        return self._execute_request(update_state_request)

    def add_workload(self, workload_name, agent, runtime="podman", runtime_config=""):
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
