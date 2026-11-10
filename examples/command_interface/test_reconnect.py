# Copyright (c) 2026 Elektrobit Automotive GmbH
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
Connects to an Ankaios server over the Command Interface and requests the
workload states every second until interrupted (Ctrl+C). Restart the server
while it runs to see the SDK reconnect: requests fail while the connection
is down and succeed again once it is back.

Usage:
    python3 test_reconnect.py [server_url]
"""

import sys
import time

from common import DEFAULT_SERVER_URL
from ankaios_sdk import Ankaios, AnkaiosException, ConnectionType

REQUEST_INTERVAL = 1.0
REQUEST_TIMEOUT = 2.0


def main() -> None:
    """Requests the workload states periodically."""
    server_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_URL

    with Ankaios(
        connection_type=ConnectionType.COMMAND_INTERFACE,
        server_url=server_url,
    ) as ankaios:
        print(f"Connected to {server_url}. Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    state = ankaios.get_state(
                        field_masks=["workloadStates"],
                        timeout=REQUEST_TIMEOUT,
                    )
                    workloads = state.get_workload_states().get_as_list()
                    print(f"get_state OK: {len(workloads)} workload(s).")
                except (AnkaiosException, TimeoutError) as e:
                    print(f"get_state failed: {e}")
                time.sleep(REQUEST_INTERVAL)
        except KeyboardInterrupt:
            print("Stopped.")


if __name__ == "__main__":
    main()
