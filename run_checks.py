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
Run checks for ankaios_sdk Python package.
This script runs unit tests, coverage, pylint and pycodestyle
checks and saves the results in the reports directory.

Example usage:
    # This will run the unit tests with the --full-trace option
    python3 run_checks.py -u --full-trace
"""

import os
import re
import pytest
import argparse
import subprocess


PROJECT_NAME = "ankaios_sdk"
REPORT_DIR = "reports"
COVERAGE_DIR = os.path.join(REPORT_DIR, "coverage")
UTEST_DIR = os.path.join(REPORT_DIR, "utest")
PYLINT_DIR = os.path.join(REPORT_DIR, "pylint")
CODESTYLE_DIR = os.path.join(REPORT_DIR, "codestyle")


def run_pytest_utest(args):
    os.makedirs(UTEST_DIR, exist_ok=True)
    result = pytest.main([
        '--junitxml={}'.format(os.path.join(UTEST_DIR, 'utest_report.xml')),
        'tests',
        # '-p', 'no:warnings',
        '-vv'
    ] + args)
    exit(result)


def run_pytest_cov(args):
    os.makedirs(COVERAGE_DIR, exist_ok=True)
    result = pytest.main([
        '--cov={}'.format(PROJECT_NAME),
        '--cov-report=html:{}'.format(os.path.join(COVERAGE_DIR, 'html')),
        '--cov-report=xml:{}'.format(os.path.join(COVERAGE_DIR, 'cov_report.xml')),
        '--cov-report=term',
        '--cov-fail-under=100',
        'tests',
        '-p', 'no:warnings',
        '-vv'
    ] + args)
    exit(result)


def run_pylint(args):
    os.makedirs(PYLINT_DIR, exist_ok=True)
    result = subprocess.run([
        'pylint', PROJECT_NAME, 'tests', '--rcfile=.pylintrc',
        '--output-format=parseable'
    ] + args, capture_output=True, text=True)
    
    pylint_output = result.stdout
    rating_line = None
    output_lines = pylint_output.split('\n')
    
    for line in output_lines:
        if 'Your code has been rated at' in line:
            rating_line = line
            break
    
    rating = 0.0
    if rating_line:
        print(rating_line)

        rating_re = re.search(r'rated at (\d+\.\d+)/10', rating_line)
        if rating_re:
            rating = float(rating_re.group(1))
    
    with open(os.path.join(PYLINT_DIR, 'pylint_report.txt'), 'w') as f:
        f.write('\n'.join(output_lines))
    if rating < 10.0:
        exit(1)


def run_pycodestyle(args):
    os.makedirs(CODESTYLE_DIR, exist_ok=True)
    result = subprocess.run([
        'pycodestyle', PROJECT_NAME, 'tests',
        '--exclude=*_pb2.py,*_pb2_grpc.py,'  # Exclude generated files
    ] + args, capture_output=True, text=True)
    
    output_lines = result.stdout.split('\n')
    if output_lines[-1] == '':
        output_lines.pop()
    print(f"PEP8 report: {len(output_lines)} violations found.")
    
    with open(os.path.join(CODESTYLE_DIR, 'codestyle_report.txt'), 'w') as f:
        f.write('\n'.join(output_lines))
    if len(output_lines) > 0:
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--cov', action='store_true', help='Run coverage')
    parser.add_argument('-u', '--utest', action='store_true', help='Run unit tests')
    parser.add_argument('-l', '--lint', action='store_true', help='Run pylint')
    parser.add_argument('-p', '--pep8', action='store_true', help='Run pep8 codestyle check')

    args, extra_args = parser.parse_known_args()
    if not any([args.cov, args.utest, args.lint, args.pep8]):
        parser.print_help()
        exit(0)
    if sum([args.cov, args.utest, args.lint, args.pep8]) > 1:
        print("Please select only one test type.")
        parser.print_help()
        exit(0)

    os.makedirs(REPORT_DIR, exist_ok=True)

    if args.cov:
        run_pytest_cov(extra_args)
    elif args.utest:
        run_pytest_utest(extra_args)
    elif args.lint:
        run_pylint(extra_args)
    elif args.pep8:
        run_pycodestyle(extra_args)
