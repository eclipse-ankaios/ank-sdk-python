# Copyright (c) 2025 Elektrobit Automotive GmbH
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
This module contains unit tests for the AccessRightRule class.
"""

from ankaios_sdk import AccessRightRule
from ankaios_sdk._protos import _ank_base


def test_state_rule():
    """
    Test a state type rule.
    """
    rule = AccessRightRule.state_rule(
        operation="Read",
        filter_masks=["mask_1", "mask_2"],
    )
    assert str(rule) == "StateRule: Read, ['mask_1', 'mask_2']"
    assert rule.type == "StateRule"
    assert rule._to_proto() == _ank_base.AccessRightsRule(
        stateRule=_ank_base.StateRule(
            operation=_ank_base.ReadWriteEnum.RW_READ,
            filterMasks=["mask_1", "mask_2"],
        )
    )
    assert rule.to_dict() == {
        "type": "StateRule",
        "operation": "Read",
        "filterMask": ["mask_1", "mask_2"],
    }


def test_log_rule():
    """
    Test a log type rule.
    """
    rule = AccessRightRule.log_rule(
        workload_names=["workload_1", "workload_2"]
    )
    assert str(rule) == "LogRule: ['workload_1', 'workload_2']"
    assert rule.type == "LogRule"
    assert rule._to_proto() == _ank_base.AccessRightsRule(
        logRule=_ank_base.LogRule(
            workloadNames=["workload_1", "workload_2"]
        )
    )
    assert rule.to_dict() == {
        "type": "LogRule",
        "workloadNames": ["workload_1", "workload_2"],
    }


def test_unknown_rule():
    """
    Test an invalid rule.
    """
    rule = AccessRightRule(
        _ank_base.AccessRightsRule()
    )
    assert str(rule) == "Unknown rule"
    assert rule.to_dict() == {
        "type": "Unknown",
    }
