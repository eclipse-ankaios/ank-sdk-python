# Copyright (c) 2024 Elektrobit Automotive GmbH
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
This module contains unit tests for the Ankaios class in the AnkaiosSDK.
"""

from io import StringIO
import logging
from unittest.mock import patch, mock_open, MagicMock
import pytest
from AnkaiosSDK import Ankaios, AnkaiosLogLevel, Response, ResponseEvent, Manifest, CompleteState
from tests.Workload.test_workload import generate_test_workload
from tests.test_request import generate_test_request
from tests.Response.test_response import MESSAGE_BUFFER_ERROR, MESSAGE_BUFFER_COMPLETE_STATE, \
    MESSAGE_BUFFER_UPDATE_SUCCESS, MESSAGE_BUFFER_UPDATE_SUCCESS_LENGTH
from tests.test_manifest import MANIFEST_DICT


def test_logger():
    """
    Test the logger functionality of the Ankaios class.
    """
    ankaios = Ankaios()
    assert ankaios.logger.level == AnkaiosLogLevel.INFO.value
    ankaios.set_logger_level(AnkaiosLogLevel.ERROR)
    assert ankaios.logger.level == AnkaiosLogLevel.ERROR.value

    str_stream = StringIO()
    handler = logging.StreamHandler(str_stream)
    ankaios.logger.addHandler(handler)

    ankaios.logger.debug("Debug message")
    assert str_stream.getvalue() == ""
    ankaios.logger.error("Error message")
    assert "Error message" in str_stream.getvalue()


def test_connection():
    """
    Test the connect / disconnect functionality of the Ankaios class.
    """
    ankaios = Ankaios()
    assert not ankaios._connected

    with patch("threading.Thread") as MockThread:
        mock_thread_instance = MagicMock()
        MockThread.return_value = mock_thread_instance

        ankaios.connect()
        MockThread.assert_called_once_with(target=ankaios._read_from_control_interface)
        mock_thread_instance.start.assert_called_once()
        assert ankaios._connected

        with pytest.raises(ValueError, match="Already connected."):
            ankaios.connect()

        ankaios.disconnect()
        mock_thread_instance.join.assert_called_once()
        assert not ankaios._connected

        with pytest.raises(ValueError, match="Already disconnected."):
            ankaios.disconnect()

        with Ankaios() as ank:
            assert ank._connected


def test_read_from_control_interface():
    """
    Test the _read_from_control_interface method of the Ankaios class.
    """
    input_file_content = MESSAGE_BUFFER_UPDATE_SUCCESS_LENGTH + \
                               MESSAGE_BUFFER_UPDATE_SUCCESS

    # Test response comes first
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.read.side_effect = [bytes([b]) for b in input_file_content]

        ankaios = Ankaios()

        # will call _read_from_control_interface
        ankaios.connect()

        # will stop the thread after reading the message
        ankaios.disconnect()

        mock_file.assert_called_once_with(
            f"{Ankaios.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb")
        assert "1234" in list(ankaios._responses)
        assert ankaios._responses["1234"].is_set()

    # Test request set first
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.read.side_effect = [bytes([b]) for b in input_file_content]

        ankaios = Ankaios()
        ankaios._responses["1234"] = ResponseEvent()

        # will call _read_from_control_interface
        ankaios.connect()

        # will stop the thread after reading the message
        ankaios.disconnect()

        mock_file.assert_called_once_with(
            f"{Ankaios.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb")
        assert "1234" in list(ankaios._responses)
        assert ankaios._responses["1234"].is_set()


def test_get_reponse_by_id():
    """
    Test the get_response_by_id method of the Ankaios class.
    """
    ankaios = Ankaios()
    with pytest.raises(ValueError, match="Reading from the control interface is not started."):
        ankaios._get_response_by_id("1234")
    ankaios._connected = True

    assert not ankaios._responses
    with patch("AnkaiosSDK.ResponseEvent.wait_for_response") as mock_wait:
        ankaios._get_response_by_id("1234")
        mock_wait.assert_called_once_with(Ankaios.DEFAULT_TIMEOUT)
        assert list(ankaios._responses.keys()) == ["1234"]
        assert isinstance(ankaios._responses["1234"], ResponseEvent)

        response = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios._responses["1234"] = ResponseEvent(response)
        assert ankaios._get_response_by_id("1234") == response
        assert not list(ankaios._responses.keys())


def test_write_to_pipe():
    """
    Test the _write_to_pipe method of the Ankaios class.
    """
    with patch("builtins.open", mock_open()) as mock_file:
        ankaios = Ankaios()
        ankaios._write_to_pipe(generate_test_request())

        mock_file.assert_called_once_with(
            f"{ankaios.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output", "ab")
        mock_file().write.assert_called()
        mock_file().flush.assert_called_once()


def test_send_request():
    """
    Test the _send_request method of the Ankaios class.
    """
    ankaios = Ankaios()
    with pytest.raises(ValueError, match="Cannot request if not connected."):
        ankaios._send_request(None)
    ankaios._connected = True

    request = generate_test_request()
    with patch("AnkaiosSDK.Ankaios._write_to_pipe") as mock_write, \
            patch("AnkaiosSDK.Ankaios._get_response_by_id") as mock_get_response:
        ankaios._send_request(request)
        mock_write.assert_called_once_with(request)
        mock_get_response.assert_called_once_with(request.get_id(), Ankaios.DEFAULT_TIMEOUT)

    with patch("AnkaiosSDK.Ankaios._write_to_pipe") as mock_write, \
            patch("AnkaiosSDK.Ankaios._get_response_by_id") as mock_get_response:
        mock_get_response.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios._send_request(request)
        mock_write.assert_called_once_with(request)


def test_apply_manifest():
    """
    Test the apply manifest method of the Ankaios class.
    """
    ankaios = Ankaios()
    ankaios.logger = MagicMock()
    manifest = Manifest(MANIFEST_DICT)

    # Test success
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios.apply_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        ankaios.apply_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        ankaios.apply_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_delete_manifest():
    """
    Test the delete manifest method of the Ankaios class.
    """
    ankaios = Ankaios()
    ankaios.logger = MagicMock()
    manifest = Manifest(MANIFEST_DICT)

    # Test success
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios.delete_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        ankaios.delete_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        ankaios.delete_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_run_workload():
    """
    Test the run workload method of the Ankaios class.
    """
    ankaios = Ankaios()
    ankaios.logger = MagicMock()
    workload = generate_test_workload()

    # Test success
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios.run_workload(workload)
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        ankaios.run_workload(workload)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        ankaios.run_workload(workload)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_delete_workload():
    """
    Test the delete workload method of the Ankaios class.
    """
    ankaios = Ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios.delete_workload("nginx")
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        ankaios.delete_workload("nginx")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        ankaios.delete_workload("nginx")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_get_workload():
    """
    Test the get workload method of the Ankaios class.
    """
    ankaios = Ankaios()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_workload") as mock_state_get_workload:
        mock_get_state.return_value = CompleteState()
        ankaios.get_workload("nginx")
        mock_get_state.assert_called_once_with(Ankaios.DEFAULT_TIMEOUT,
                                               ["desiredState.workloads.nginx"])
        mock_state_get_workload.assert_called_once_with("nginx")

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_workload") as mock_state_get_workload:
        ankaios.get_workload("nginx", state=CompleteState())
        mock_get_state.assert_not_called()
        mock_state_get_workload.assert_called_once_with("nginx")

def test_set_config():
    """
    Test the set config methods of the Ankaios class.
    """
    ankaios = Ankaios()

    with patch("builtins.open", mock_open()) as mock_file, \
            patch("AnkaiosSDK.Ankaios.set_config") as mock_set_config:
        mock_file().read.return_value = {'config_test': 'value'}
        ankaios.set_config_from_file(name="config_test", config_path=r"path/to/config")

        mock_file.assert_called_with(r"path/to/config", "r", encoding="utf-8")
        mock_file().read.assert_called_once()
        mock_set_config.assert_called_once_with("config_test", {'config_test': 'value'})

    with pytest.raises(NotImplementedError, match="not implemented yet"):
        ankaios.set_config(name="config_test", config={'config_test': 'value'})


def test_get_config():
    """
    Test the get config method of the Ankaios class.
    """
    ankaios = Ankaios()

    with pytest.raises(NotImplementedError, match="not implemented yet"):
        ankaios.get_config(name="config_test")


def test_delete_config():
    """
    Test the delete config method of the Ankaios class.
    """
    ankaios = Ankaios()

    with pytest.raises(NotImplementedError, match="not implemented yet"):
        ankaios.delete_config(name="config_test")


def test_get_state():
    """
    Test the get state method of the Ankaios class.
    """
    ankaios = Ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_COMPLETE_STATE)
        result = ankaios.get_state()
        mock_send_request.assert_called_once()
        assert isinstance(result, CompleteState)

    # Test error
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        result = ankaios.get_state(field_mask=["invalid_mask"])
        mock_send_request.assert_called_once()
        assert result is None
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("AnkaiosSDK.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        result = ankaios.get_state()
        mock_send_request.assert_called_once()
        assert result is None
        ankaios.logger.error.assert_called()


def test_get_agents():
    """
    Test the get agents method of the Ankaios class.
    """
    ankaios = Ankaios()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_agents") as mock_state_get_agents:
        mock_get_state.return_value = CompleteState()
        ankaios.get_agents()
        mock_get_state.assert_called_once_with(Ankaios.DEFAULT_TIMEOUT)
        mock_state_get_agents.assert_called_once()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_agents") as mock_state_get_agents:
        ankaios.get_agents(state=CompleteState())
        mock_get_state.assert_not_called()
        mock_state_get_agents.assert_called_once()


def test_get_workload_states():
    """
    Test the get workload states method of the Ankaios class.
    """
    ankaios = Ankaios()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_workload_states") as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        ankaios.get_workload_states()
        mock_get_state.assert_called_once_with(Ankaios.DEFAULT_TIMEOUT)
        mock_state_get_workload_states.assert_called_once()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_workload_states") as mock_state_get_workload_states:
        ankaios.get_workload_states(state=CompleteState())
        mock_get_state.assert_not_called()
        mock_state_get_workload_states.assert_called_once()


def test_get_workload_states_on_agent():
    """
    Test the get workload states on agent method of the Ankaios class.
    """
    ankaios = Ankaios()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_workload_states") as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        ankaios.get_workload_states_on_agent("agent_A")
        mock_get_state.assert_called_once_with(Ankaios.DEFAULT_TIMEOUT, ["workloadStates.agent_A"])
        mock_state_get_workload_states.assert_called_once()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_workload_states") as mock_state_get_workload_states:
        ankaios.get_workload_states_on_agent("agent_A", state=CompleteState())
        mock_get_state.assert_not_called()
        mock_state_get_workload_states.assert_called_once()


def test_get_workload_states_on_workload_name():
    """
    Test the get workload states on workload name method of the Ankaios class.
    """
    ankaios = Ankaios()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_workload_states") as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        ankaios.get_workload_states_on_workload_name("nginx")
        mock_get_state.assert_called_once_with(Ankaios.DEFAULT_TIMEOUT, ["workloadStates.nginx"])
        mock_state_get_workload_states.assert_called_once()

    with patch("AnkaiosSDK.Ankaios.get_state") as mock_get_state, \
            patch("AnkaiosSDK.CompleteState.get_workload_states") as mock_state_get_workload_states:
        ankaios.get_workload_states_on_workload_name("nginx", state=CompleteState())
        mock_get_state.assert_not_called()
        mock_state_get_workload_states.assert_called_once()
