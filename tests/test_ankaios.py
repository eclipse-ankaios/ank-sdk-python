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
This module contains unit tests for the Ankaios class in the ankaios_sdk.
"""

from io import StringIO
import logging
from unittest.mock import patch, MagicMock
import pytest
from ankaios_sdk import Ankaios, AnkaiosLogLevel, Response, ResponseEvent, \
    UpdateStateSuccess, Manifest, CompleteState, WorkloadInstanceName, \
    WorkloadStateCollection, WorkloadStateEnum, ControlInterfaceState, \
    AnkaiosProtocolException, AnkaiosResponseError
from ankaios_sdk.utils import WORKLOADS_PREFIX
from tests.workload.test_workload import generate_test_workload
from tests.test_request import generate_test_request
from tests.response.test_response import MESSAGE_BUFFER_ERROR, \
    MESSAGE_BUFFER_COMPLETE_STATE, MESSAGE_BUFFER_UPDATE_SUCCESS
from tests.test_manifest import MANIFEST_DICT
from tests.workload_state.test_workload_state import \
    generate_test_workload_state


def generate_test_ankaios() -> Ankaios:
    """
    Helper function to generate an Ankaios instance without connecting to the
    control interface.

    Returns:
        Ankaios: The Ankaios instance.
    """
    with patch("ankaios_sdk.ControlInterface.connect") as mock_connect:
        ankaios = Ankaios()
        mock_connect.assert_called_once()
    ankaios._control_interface._state = ControlInterfaceState.INITIALIZED
    return ankaios


def test_logger():
    """
    Test the logger functionality of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
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
    Test the connect and disconnect of the Ankaios class.
    """
    with patch("ankaios_sdk.ControlInterface.connect") as mock_ci_connect, \
         patch("ankaios_sdk.ControlInterface.disconnect") \
            as mock_ci_disconnect:
        with Ankaios() as ankaios:
            assert isinstance(ankaios, Ankaios)
            mock_ci_connect.assert_called_once()
            assert ankaios.logger.level == AnkaiosLogLevel.INFO.value
        mock_ci_disconnect.assert_called_once()


def test_state():
    """
    Test the state property of the Ankaios class and the state callback.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    assert ankaios.state == ankaios._control_interface._state
    ankaios._state_changed(ControlInterfaceState.TERMINATED)
    ankaios.logger.info.assert_called_with(
        "State changed to %s", ControlInterfaceState.TERMINATED
    )


def test_add_response():
    """
    Test the _add_response method of the Ankaios class.
    This method is called from the ControlInterface when a response
    is received.
    """
    response = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)

    # Test response comes first
    ankaios = generate_test_ankaios()
    ankaios._add_response(response)
    assert "1234" in list(ankaios._responses)
    assert ankaios._responses["1234"].is_set()

    # Test request set first
    ankaios = generate_test_ankaios()
    ankaios._responses["1234"] = ResponseEvent()
    ankaios._add_response(response)
    assert "1234" in list(ankaios._responses)
    assert ankaios._responses["1234"].is_set()


def test_get_reponse_by_id():
    """
    Test the get_response_by_id method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    assert not ankaios._responses
    with patch("ankaios_sdk.ResponseEvent.wait_for_response") as mock_wait:
        ankaios._get_response_by_id("1234")
        mock_wait.assert_called_once_with(Ankaios.DEFAULT_TIMEOUT)
        assert list(ankaios._responses.keys()) == ["1234"]
        assert isinstance(ankaios._responses["1234"], ResponseEvent)

        response = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios._responses["1234"] = ResponseEvent(response)
        assert ankaios._get_response_by_id("1234") == response
        assert not list(ankaios._responses.keys())


def test_send_request():
    """
    Test the _send_request method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    request = generate_test_request()
    with patch("ankaios_sdk.ControlInterface.write_request") as mock_write, \
            patch("ankaios_sdk.Ankaios._get_response_by_id") \
            as mock_get_response:
        ankaios._send_request(request)
        mock_write.assert_called_once_with(request)
        mock_get_response.assert_called_once_with(
            request.get_id(), Ankaios.DEFAULT_TIMEOUT
        )

    with patch("ankaios_sdk.ControlInterface.write_request") as mock_write, \
            patch("ankaios_sdk.Ankaios._get_response_by_id") \
            as mock_get_response:
        mock_get_response.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios._send_request(request)
        mock_write.assert_called_once_with(request)


def test_apply_manifest():
    """
    Test the apply manifest method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    manifest = Manifest(MANIFEST_DICT)

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ret = ankaios.apply_manifest(manifest)
        assert isinstance(ret, UpdateStateSuccess)
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.apply_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.apply_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.apply_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_delete_manifest():
    """
    Test the delete manifest method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    manifest = Manifest(MANIFEST_DICT)

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ret = ankaios.delete_manifest(manifest)
        assert isinstance(ret, UpdateStateSuccess)
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.delete_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.delete_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.delete_manifest(manifest)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_apply_workload():
    """
    Test the apply workload method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    workload = generate_test_workload()

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ret = ankaios.apply_workload(workload)
        assert isinstance(ret, UpdateStateSuccess)
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.apply_workload(workload)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.apply_workload(workload)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.apply_workload(workload)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_get_workload():
    """
    Test the get workload of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    workload_name = "nginx"
    workload = generate_test_workload(
        workload_name=workload_name
    )

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_workloads") \
            as mock_state_get_workloads:
        mock_get_state.return_value = CompleteState()
        mock_state_get_workloads.return_value = [workload]
        ret = ankaios.get_workload(workload_name)
        assert ret == workload
        mock_get_state.assert_called_once_with(
            [f"{WORKLOADS_PREFIX}.nginx"],
            Ankaios.DEFAULT_TIMEOUT
        )
        mock_state_get_workloads.assert_called_once()


def test_delete_workload():
    """
    Test the delete workload method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ret = ankaios.delete_workload("nginx")
        assert isinstance(ret, UpdateStateSuccess)
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.delete_workload("nginx")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.delete_workload("nginx")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.delete_workload("nginx")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_update_configs():
    """
    Test the update configs method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios.update_configs({"name": "config"})
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.update_configs({"name": "config"})
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.update_configs({"name": "config"})
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.update_configs({"name": "config"})
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_add_config():
    """
    Test the add config method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios.add_config("name", "config")
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.add_config("name", "config")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.add_config("name", "config")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.add_config("name", "config")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_get_configs():
    """
    Test the get configs method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_configs") \
            as mock_state_get_configs:
        mock_get_state.return_value = CompleteState()
        ankaios.get_configs()
        mock_get_state.assert_called_once_with(
            field_masks=['desiredState.configs']
            )
        mock_state_get_configs.assert_called_once()


def test_get_config():
    """
    Test the get config method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_configs") \
            as mock_state_get_configs:
        mock_get_state.return_value = CompleteState()
        ankaios.get_config("config_name")
        mock_get_state.assert_called_once_with(
                field_masks=['desiredState.configs.config_name']
            )
        mock_state_get_configs.assert_called_once()


def test_delete_all_configs():
    """
    Test the delete all configs method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios.delete_all_configs()
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.delete_all_configs()
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.delete_all_configs()
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.delete_all_configs()
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_delete_config():
    """
    Test the delete config method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        ankaios.delete_config("config_name")
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.delete_config("config_name")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.delete_config("config_name")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.delete_config("config_name")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_get_state():
    """
    Test the get state method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_COMPLETE_STATE)
        ret = ankaios.get_state()
        mock_send_request.assert_called_once()
        assert isinstance(ret, CompleteState)

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.get_state(field_masks=["invalid_mask"])
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.get_state()
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = \
            Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
        with pytest.raises(AnkaiosProtocolException):
            ankaios.get_state()
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_get_agents():
    """
    Test the get agents method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_agents") \
            as mock_state_get_agents:
        mock_get_state.return_value = CompleteState()
        ankaios.get_agents()
        mock_get_state.assert_called_once_with(
            None, Ankaios.DEFAULT_TIMEOUT
            )
        mock_state_get_agents.assert_called_once()


def test_get_workload_states():
    """
    Test the get workload states method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_workload_states") \
            as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        ankaios.get_workload_states()
        mock_get_state.assert_called_once_with(
            None, Ankaios.DEFAULT_TIMEOUT
            )
        mock_state_get_workload_states.assert_called_once()


def test_get_execution_state_for_instance_name():
    """
    Test the get execution state for instance name method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    workload_instance_name = WorkloadInstanceName(
        agent_name="agent_Test",
        workload_name="workload_Test",
        workload_id="1234"
    )

    # State does not contain the required workload state
    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_workload_states") \
            as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        with pytest.raises(AnkaiosProtocolException):
            ankaios.get_execution_state_for_instance_name(
                workload_instance_name)
        mock_state_get_workload_states.assert_called_once()
        ankaios.logger.error.assert_called()

    # State contains the required workload state
    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_workload_states") \
            as mock_state_get_workload_states, \
            patch("ankaios_sdk.WorkloadStateCollection.get_as_list") \
            as mock_state_get_as_list:
        mock_get_state.return_value = CompleteState()
        mock_state_get_workload_states.return_value = WorkloadStateCollection()
        workload_state = MagicMock()
        workload_state.execution_state = MagicMock()
        mock_state_get_as_list.return_value = [workload_state]
        assert ankaios.get_execution_state_for_instance_name(
            workload_instance_name
            ) == workload_state.execution_state


def test_get_workload_states_on_agent():
    """
    Test the get workload states on agent method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_workload_states") \
            as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        ankaios.get_workload_states_on_agent("agent_A")
        mock_get_state.assert_called_once_with(
            ["workloadStates.agent_A"],
            Ankaios.DEFAULT_TIMEOUT
        )
        mock_state_get_workload_states.assert_called_once()


def test_get_workload_states_for_name():
    """
    Test the get workload states for workload name method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, \
            patch("ankaios_sdk.CompleteState.get_workload_states") \
            as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        wl_state_collection = WorkloadStateCollection()
        wl_state = generate_test_workload_state()
        wl_state_collection.add_workload_state(wl_state)
        mock_state_get_workload_states.return_value = wl_state_collection
        ret = ankaios.get_workload_states_for_name("workload_Test")
        assert isinstance(ret, WorkloadStateCollection)
        wl_list = ret.get_as_list()
        assert len(wl_list) == 1
        assert str(wl_list[0]) == str(wl_state)


def test_wait_for_workload_to_reach_state():
    """
    Test the wait for workload to reach state method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    instance_name = WorkloadInstanceName(
        agent_name="agent_Test",
        workload_name="workload_Test",
        workload_id="1234"
    )

    # Test timeout
    with patch("ankaios_sdk.Ankaios.get_execution_state_for_instance_name") \
            as mock_get_state:
        mock_get_state.return_value = MagicMock()
        mock_get_state().state = WorkloadStateEnum.FAILED
        with pytest.raises(TimeoutError):
            ankaios.wait_for_workload_to_reach_state(
                instance_name, WorkloadStateEnum.RUNNING,
                timeout=0.01
            )
        mock_get_state.assert_called()

    # Test success
    with patch("ankaios_sdk.Ankaios.get_execution_state_for_instance_name") \
            as mock_get_state:
        mock_get_state.return_value = MagicMock()
        mock_get_state().state = WorkloadStateEnum.RUNNING
        ankaios.wait_for_workload_to_reach_state(
            instance_name, WorkloadStateEnum.RUNNING
        )
        mock_get_state.assert_called()
