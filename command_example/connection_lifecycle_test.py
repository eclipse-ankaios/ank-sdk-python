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
Connects to an Ankaios server over the Command Interface several times in
a row, printing the workload states each time. The server URL can be a TCP
one (http://...) or a Unix domain socket one (unix://...).

Usage:
    python3 connection_lifecycle_test.py [server_url]
"""

import sys

from common import DEFAULT_SERVER_URL, print_workload_states
from ankaios_sdk import Ankaios, ConnectionType

CONNECT_ATTEMPTS = 3


def main() -> None:
    """Connects and disconnects several times in a row."""
    server_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_URL

    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        with Ankaios(
            connection_type=ConnectionType.COMMAND_INTERFACE,
            server_url=server_url,
        ) as ankaios:
            print(f"Connection {attempt}/{CONNECT_ATTEMPTS} established.")
            print_workload_states(ankaios)


if __name__ == "__main__":
    main()
