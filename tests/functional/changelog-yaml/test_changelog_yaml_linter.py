"""
Test changelog.yaml linting.
"""
import glob
import json
import os.path

import pytest

from antsibull.changelog.lint import lint_changelog_yaml


# Collect files
PATTERNS = ['*.yml', '*.yaml']
BASE_DIR = os.path.dirname(__file__)
GOOD_TESTS = []
BAD_TESTS = []

for pattern in PATTERNS:
    for filename in glob.glob(os.path.join(BASE_DIR, 'good', pattern)):
        GOOD_TESTS.append(filename)
    for filename in glob.glob(os.path.join(BASE_DIR, 'bad', pattern)):
        json_filename = os.path.splitext(filename)[0] + '.json'
        if os.path.exists(json_filename):
            BAD_TESTS.append((filename, json_filename))
        else:
            pytest.fail('Missing {0} for {1}'.format(json_filename, filename))

# Test good files
@pytest.mark.parametrize('yaml_filename', GOOD_TESTS)
def test_good_changelog_yaml_files(yaml_filename):
    errors = lint_changelog_yaml(yaml_filename)
    assert len(errors) == 0

@pytest.mark.parametrize('yaml_filename, json_filename', BAD_TESTS)
def test_bad_changelog_yaml_files(yaml_filename, json_filename):
    errors = lint_changelog_yaml(yaml_filename)
    assert len(errors) > 0

    # Cut off path
    errors = [list(error[1:]) for error in errors]
    # Load expected errors
    with open(json_filename, 'r') as json_f:
        data = json.load(json_f)

    assert errors == data['errors']
