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

import os
import pytest
import argparse
import subprocess


PROJECT_NAME = "AnkaiosSDK"
REPORT_DIR = "reports"
COVERAGE_DIR = os.path.join(REPORT_DIR, "coverage")
UTEST_DIR = os.path.join(REPORT_DIR, "utest")
PYLINT_DIR = os.path.join(REPORT_DIR, "pylint")


def run_pytest_utest():
    os.makedirs(UTEST_DIR, exist_ok=True)
    pytest.main([
        '--junitxml={}'.format(os.path.join(UTEST_DIR, 'utest_report.xml')),
        'tests',
        # '-p', 'no:warnings',
        '-vv'
    ])


def run_pytest_cov():
    os.makedirs(COVERAGE_DIR, exist_ok=True)
    pytest.main([
        '--cov={}'.format(PROJECT_NAME),
        '--cov-report=html:{}'.format(os.path.join(COVERAGE_DIR, 'html')),
        '--cov-report=xml:{}'.format(os.path.join(COVERAGE_DIR, 'cov_report.xml')),
        '--cov-report=term',
        'tests',
        '-p', 'no:warnings',
        '-vv'
    ])


def run_pylint():
    os.makedirs(PYLINT_DIR, exist_ok=True)
    result = subprocess.run([
        'pylint', PROJECT_NAME, 'tests', '--rcfile=.pylintrc', '--output-format=parseable'
    ], capture_output=True, text=True)
    
    pylint_output = result.stdout
    rating_line = None
    output_lines = pylint_output.split('\n')
    
    for line in output_lines:
        if 'Your code has been rated at' in line:
            rating_line = line
            break
    
    if rating_line:
        print(rating_line)
    
    with open(os.path.join(PYLINT_DIR, 'pylint_report.txt'), 'w') as f:
        f.write('\n'.join(output_lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f'Run tests for {PROJECT_NAME} Python package')
    parser.add_argument('-c', '--cov', action='store_true', help='Run coverage')
    parser.add_argument('-u', '--utest', action='store_true', help='Run unit tests')
    parser.add_argument('-l', '--lint', action='store_true', help='Run pylint')
    parser.add_argument('-a', '--all', action='store_true', help='Run all tests')

    args = parser.parse_args()
    if not any([args.cov, args.utest, args.lint, args.all]):
        parser.print_help()
        exit(0)
    os.makedirs(REPORT_DIR, exist_ok=True)

    if args.cov or args.all:
        run_pytest_cov()
    if args.utest or args.all:
        run_pytest_utest()
    if args.lint or args.all:
        run_pylint()
