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

# pylint: disable=too-many-lines

from io import StringIO
import logging
from unittest.mock import patch, MagicMock, PropertyMock
import pytest
from ankaios_sdk import (
    Ankaios,
    AnkaiosLogLevel,
    LogEntry,
    Response,
    UpdateStateSuccess,
    Manifest,
    CompleteState,
    WorkloadInstanceName,
    WorkloadStateCollection,
    WorkloadStateEnum,
    ControlInterfaceState,
    AnkaiosProtocolException,
    AnkaiosResponseError,
    ConnectionClosedException,
    LogCampaignResponse,
    LogsCancelRequest,
    EventQueue,
    EventsCancelRequest,
)
from ankaios_sdk.utils import WORKLOADS_PREFIX
from tests.workload.test_workload import generate_test_workload
from tests.request.test_request import generate_test_request
from tests.response.test_response import (
    generate_test_log_entry,
    MESSAGE_BUFFER_ERROR,
    MESSAGE_BUFFER_COMPLETE_STATE,
    MESSAGE_BUFFER_UPDATE_SUCCESS,
    MESSAGE_BUFFER_CONNECTION_CLOSED,
    MESSAGE_BUFFER_LOGS_REQUEST_ACCEPTED,
    MESSAGE_BUFFER_LOGS_CANCEL_REQUEST_ACCEPTED,
    MESSAGE_BUFFER_EVENTS_CANCEL_ACCEPTED_RESPONSE,
)
from tests.test_manifest import MANIFEST_DICT
from tests.workload_state.test_workload_state import (
    generate_test_workload_state,
)
from tests.test_event_campaign import generate_test_event_entry


def generate_test_ankaios() -> Ankaios:
    """
    Helper function to generate an Ankaios instance without connecting to the
    control interface.

    Returns:
        Ankaios: The Ankaios instance.
    """
    with patch("ankaios_sdk.ControlInterface.connect") as mock_connect, patch(
        "ankaios_sdk.ControlInterface.connected", new_callable=PropertyMock
    ) as mock_connected:
        mock_connected.return_value = True
        ankaios = Ankaios()
        mock_connect.assert_called_once()
    ankaios._control_interface._state = ControlInterfaceState.CONNECTED
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


def test_connect_disconnect():
    """
    Test the connect and disconnect of the Ankaios class.
    """
    with patch(
        "ankaios_sdk.ControlInterface.connect"
    ) as mock_ci_connect, patch(
        "ankaios_sdk.ControlInterface.connected", new_callable=PropertyMock
    ) as mock_ci_connected, patch(
        "ankaios_sdk.ControlInterface.disconnect"
    ) as mock_ci_disconnect:
        mock_ci_connected.return_value = True
        with Ankaios() as ankaios:
            assert isinstance(ankaios, Ankaios)
            mock_ci_connect.assert_called_once()
            assert ankaios.logger.level == AnkaiosLogLevel.INFO.value
        mock_ci_disconnect.assert_called_once()


def test_connection_timeout():
    """
    Test the connection timeout case.
    """
    with patch("time.time") as mock_time, patch("time.sleep"), patch(
        "ankaios_sdk.ControlInterface.connect"
    ) as mock_ci_connect, patch(
        "ankaios_sdk.ControlInterface.disconnect"
    ) as _, patch(
        "ankaios_sdk.ControlInterface.connected", new_callable=PropertyMock
    ) as mock_ci_connected:
        # The first 2 values are needed to call the sleep
        # The last 2 values are needed to exceed the timeout properly
        mock_time.side_effect = [100.0, 101.0, 105.1, 105.1]
        mock_ci_connected.return_value = False
        with pytest.raises(ConnectionClosedException):
            _ = Ankaios()
        mock_ci_connect.assert_called_once()


def test_add_response():
    """
    Test the _add_response method of the Ankaios class.
    This method is called from the ControlInterface when a response
    is received.
    """
    response = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)

    ankaios = generate_test_ankaios()
    assert ankaios._responses.empty()
    ankaios._add_response(response)
    assert ankaios._responses.qsize() == 1
    assert ankaios._responses.get() == response
    assert ankaios._responses.empty()


def test_add_logs():
    """
    Test the _add_logs method of the Ankaios class.
    This method is called from the ControlInterface when a response
    of type Logs Entries is received.
    """
    log_entries = [
        LogEntry._from_entries(generate_test_log_entry(name="nginx_A")),
        LogEntry._from_entries(generate_test_log_entry(name="nginx_B")),
    ]
    add_logs_cb_mock = MagicMock()

    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    assert len(ankaios._logs_callbacks) == 0
    ankaios._logs_callbacks = {"correct_id": add_logs_cb_mock}
    ankaios._add_logs("correct_id", log_entries)
    assert add_logs_cb_mock.call_count == 2
    ankaios.logger.warning.assert_not_called()

    ankaios._add_logs("wrong_id", log_entries)
    assert add_logs_cb_mock.call_count == 2
    ankaios.logger.warning.assert_called_once()


def test_add_events():
    """
    Test the _add_events method of the Ankaios class.
    This method is called from the ControlInterface when a response
    of type EventEntry is received.
    """
    event_entry = generate_test_event_entry()
    add_event_cb_mock = MagicMock()

    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    assert len(ankaios._events_callbacks) == 0
    ankaios._events_callbacks = {"correct_id": add_event_cb_mock}
    ankaios._add_events("correct_id", event_entry)
    assert add_event_cb_mock.call_count == 1
    ankaios.logger.warning.assert_not_called()

    ankaios._add_events("wrong_id", event_entry)
    assert add_event_cb_mock.call_count == 1
    ankaios.logger.warning.assert_called_once()


def test_get_reponse_by_id():
    """
    Test the get_response_by_id method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    assert ankaios._responses.empty()

    response = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)  # 3344
    ankaios._responses.put(Response(MESSAGE_BUFFER_COMPLETE_STATE))
    ankaios._responses.put(response)
    assert ankaios._responses.qsize() == 2
    assert ankaios._get_response_by_id("3344") == response
    assert ankaios._responses.empty()

    with pytest.raises(TimeoutError):
        ankaios._responses.put(Response(MESSAGE_BUFFER_COMPLETE_STATE))
        ankaios._get_response_by_id("3344", timeout=0.01)

    with pytest.raises(ConnectionClosedException):
        ankaios._responses.put(Response(MESSAGE_BUFFER_CONNECTION_CLOSED))
        ankaios._get_response_by_id("1122")


def test_send_request():
    """
    Test the _send_request method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    request = generate_test_request()
    with patch(
        "ankaios_sdk.ControlInterface.write_request"
    ) as mock_write, patch(
        "ankaios_sdk.Ankaios._get_response_by_id"
    ) as mock_get_response:
        ankaios._send_request(request)
        mock_write.assert_called_once_with(request)
        mock_get_response.assert_called_once_with(
            request.get_id(), Ankaios.DEFAULT_TIMEOUT
        )

    with patch(
        "ankaios_sdk.ControlInterface.write_request"
    ) as mock_write, patch(
        "ankaios_sdk.Ankaios._get_response_by_id"
    ) as mock_get_response:
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
    manifest = Manifest.from_dict(MANIFEST_DICT)

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
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
    manifest = Manifest.from_dict(MANIFEST_DICT)

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
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
    workload = generate_test_workload(workload_name=workload_name)

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_workloads"
    ) as mock_state_get_workloads:
        mock_get_state.return_value = CompleteState()
        mock_state_get_workloads.return_value = [workload]
        ret = ankaios.get_workload(workload_name)
        assert ret == [workload]
        mock_get_state.assert_called_once_with(
            [f"{WORKLOADS_PREFIX}.nginx"], Ankaios.DEFAULT_TIMEOUT
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
        with pytest.raises(AnkaiosProtocolException):
            ankaios.add_config("name", "config")
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_get_configs():
    """
    Test the get configs method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_configs"
    ) as mock_state_get_configs:
        mock_get_state.return_value = CompleteState()
        ankaios.get_configs()
        mock_get_state.assert_called_once_with(
            field_masks=["desiredState.configs"]
        )
        mock_state_get_configs.assert_called_once()


def test_get_config():
    """
    Test the get config method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_configs"
    ) as mock_state_get_configs:
        mock_get_state.return_value = CompleteState()
        ankaios.get_config("config_name")
        mock_get_state.assert_called_once_with(
            field_masks=["desiredState.configs.config_name"]
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
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
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
        with pytest.raises(AnkaiosProtocolException):
            ankaios.get_state()
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_set_agent_tags():
    """
    Test the set_agent_tags method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
        ankaios.set_agent_tags("agent_A", {"updated_tag": "value"})
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.set_agent_tags("agent_A", {"updated_tag": "value"})
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.set_agent_tags("agent_A", {"updated_tag": "value"})
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
        with pytest.raises(AnkaiosProtocolException):
            ankaios.set_agent_tags("agent_A", {"updated_tag": "value"})
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_get_agents():
    """
    Test the get agents method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_agents"
    ) as mock_state_get_agents:
        mock_get_state.return_value = CompleteState()
        ankaios.get_agents()
        mock_get_state.assert_called_once_with(
            ["agents"], Ankaios.DEFAULT_TIMEOUT
        )
        mock_state_get_agents.assert_called_once()


def test_get_agent():
    """
    Test the get agent method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    agent_name = "agent_A"
    agent_attributes = MagicMock()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_agents"
    ) as mock_state_get_agents:
        mock_get_state.return_value = CompleteState()
        mock_state_get_agents.return_value = {agent_name: agent_attributes}
        ret = ankaios.get_agent(agent_name)
        assert ret == agent_attributes
        mock_get_state.assert_called_once_with(
            field_masks=[f"agents.{agent_name}"],
            timeout=Ankaios.DEFAULT_TIMEOUT,
        )
        mock_state_get_agents.assert_called_once()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_agents"
    ) as mock_state_get_agents:
        mock_get_state.return_value = CompleteState()
        mock_state_get_agents.return_value = {
            "another_agent": agent_attributes
        }

        with pytest.raises(
            AnkaiosProtocolException,
            match="Agent agent_A not found",
        ):
            ankaios.get_agent(agent_name)

        mock_get_state.assert_called_once_with(
            field_masks=[f"agents.{agent_name}"],
            timeout=Ankaios.DEFAULT_TIMEOUT,
        )
        mock_state_get_agents.assert_called_once()


def test_get_workload_states():
    """
    Test the get workload states method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_workload_states"
    ) as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        ankaios.get_workload_states()
        mock_get_state.assert_called_once_with(
            ["workloadStates"], Ankaios.DEFAULT_TIMEOUT
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
        workload_id="1234",
    )

    # State does not contain the required workload state
    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_workload_states"
    ) as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        with pytest.raises(AnkaiosProtocolException):
            ankaios.get_execution_state_for_instance_name(
                workload_instance_name
            )
        mock_state_get_workload_states.assert_called_once()
        ankaios.logger.error.assert_called()

    # State contains the required workload state
    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_workload_states"
    ) as mock_state_get_workload_states, patch(
        "ankaios_sdk.WorkloadStateCollection.get_as_list"
    ) as mock_state_get_as_list:
        mock_get_state.return_value = CompleteState()
        mock_state_get_workload_states.return_value = WorkloadStateCollection()
        workload_state = MagicMock()
        workload_state.execution_state = MagicMock()
        mock_state_get_as_list.return_value = [workload_state]
        assert (
            ankaios.get_execution_state_for_instance_name(
                workload_instance_name
            )
            == workload_state.execution_state
        )


def test_get_workload_states_on_agent():
    """
    Test the get workload states on agent method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_workload_states"
    ) as mock_state_get_workload_states:
        mock_get_state.return_value = CompleteState()
        ankaios.get_workload_states_on_agent("agent_A")
        mock_get_state.assert_called_once_with(
            ["workloadStates.agent_A"], Ankaios.DEFAULT_TIMEOUT
        )
        mock_state_get_workload_states.assert_called_once()


def test_get_workload_states_for_name():
    """
    Test the get workload states for workload name method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()

    with patch("ankaios_sdk.Ankaios.get_state") as mock_get_state, patch(
        "ankaios_sdk.CompleteState.get_workload_states"
    ) as mock_state_get_workload_states:
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
        workload_id="1234",
    )

    # Test timeout
    with patch(
        "ankaios_sdk.Ankaios.get_execution_state_for_instance_name"
    ) as mock_get_state:
        mock_get_state.return_value = MagicMock()
        mock_get_state().state = WorkloadStateEnum.FAILED
        with pytest.raises(TimeoutError):
            ankaios.wait_for_workload_to_reach_state(
                instance_name, WorkloadStateEnum.RUNNING, timeout=0.01
            )
        mock_get_state.assert_called()

    # Test success
    with patch(
        "ankaios_sdk.Ankaios.get_execution_state_for_instance_name"
    ) as mock_get_state:
        mock_get_state.return_value = MagicMock()
        mock_get_state().state = WorkloadStateEnum.RUNNING
        ankaios.wait_for_workload_to_reach_state(
            instance_name, WorkloadStateEnum.RUNNING
        )
        mock_get_state.assert_called()


def test_request_logs():
    """
    Test the request_logs method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    workload_instance_name = WorkloadInstanceName(
        agent_name="agent_A", workload_name="nginx", workload_id="1234"
    )
    assert len(ankaios._logs_callbacks) == 0

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_LOGS_REQUEST_ACCEPTED
        )
        log_campaign = ankaios.request_logs([workload_instance_name])
        request = mock_send_request.call_args[0][0]
        assert isinstance(log_campaign, LogCampaignResponse)
        assert len(ankaios._logs_callbacks) == 1
        assert (
            ankaios._logs_callbacks[request.get_id()] == log_campaign.queue.put
        )
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.request_logs([workload_instance_name])
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.request_logs([workload_instance_name])
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
        with pytest.raises(AnkaiosProtocolException):
            ankaios.request_logs([workload_instance_name])
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_stop_receiving_logs():
    """
    Test the stop_receiving_logs method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    workload_instance_name = WorkloadInstanceName(
        agent_name="agent_A", workload_name="nginx", workload_id="1234"
    )
    assert len(ankaios._logs_callbacks) == 0

    # Populate the logs callback with a campaign
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_LOGS_REQUEST_ACCEPTED
        )
        log_campaign = ankaios.request_logs([workload_instance_name])
        assert isinstance(log_campaign, LogCampaignResponse)
        assert len(ankaios._logs_callbacks) == 1

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_LOGS_CANCEL_REQUEST_ACCEPTED
        )
        cancel_request = LogsCancelRequest(log_campaign.queue._request_id)
        ankaios.stop_receiving_logs(log_campaign)
        request = mock_send_request.call_args[0][0]
        assert cancel_request._to_proto() == request._to_proto()
        assert len(ankaios._logs_callbacks) == 0
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.stop_receiving_logs(log_campaign)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.stop_receiving_logs(log_campaign)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
        with pytest.raises(AnkaiosProtocolException):
            ankaios.stop_receiving_logs(log_campaign)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_register_events():
    """
    Test the register_event method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    assert len(ankaios._events_callbacks) == 0

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
        events_queue = ankaios.register_event(field_masks=["field1"])
        request = mock_send_request.call_args[0][0]
        assert isinstance(events_queue, EventQueue)
        assert len(ankaios._events_callbacks) == 1
        # pylint: disable=comparison-with-callable
        assert (
            ankaios._events_callbacks[request.get_id()]
            == events_queue.add_event
        )
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.register_event(field_masks=["field1"])
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.register_event(field_masks=["field1"])
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
        with pytest.raises(AnkaiosProtocolException):
            ankaios.register_event(field_masks=["field1"])
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()


def test_unregister_event():
    """
    Test the unregister_event method of the Ankaios class.
    """
    ankaios = generate_test_ankaios()
    ankaios.logger = MagicMock()
    assert len(ankaios._events_callbacks) == 0

    # Populate the events callback with a campaign
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_COMPLETE_STATE
        )
        events_queue = ankaios.register_event(field_masks=["field1"])
        assert isinstance(events_queue, EventQueue)
        assert len(ankaios._events_callbacks) == 1

    # Test success
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_EVENTS_CANCEL_ACCEPTED_RESPONSE
        )
        cancel_request = EventsCancelRequest(
            request_id=events_queue._request_id
        )
        ankaios.unregister_event(events_queue)
        request = mock_send_request.call_args[0][0]
        assert cancel_request._to_proto() == request._to_proto()
        assert len(ankaios._events_callbacks) == 0
        mock_send_request.assert_called_once()
        ankaios.logger.info.assert_called()

    # Test error
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(MESSAGE_BUFFER_ERROR)
        with pytest.raises(AnkaiosResponseError):
            ankaios.unregister_event(events_queue)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test timeout
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            ankaios.unregister_event(events_queue)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()

    # Test invalid content type
    with patch("ankaios_sdk.Ankaios._send_request") as mock_send_request:
        mock_send_request.return_value = Response(
            MESSAGE_BUFFER_UPDATE_SUCCESS
        )
        with pytest.raises(AnkaiosProtocolException):
            ankaios.unregister_event(events_queue)
        mock_send_request.assert_called_once()
        ankaios.logger.error.assert_called()
