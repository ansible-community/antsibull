# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from pathlib import Path
from unittest.mock import patch

import pytest
from antsibull_core.yaml import load_yaml_file

from antsibull_build.cli.antsibull_build import run


@pytest.mark.parametrize(
    "args, expected, ret",
    [
        pytest.param(
            [],
            [
                "cisco.nso 1.0.3 is not tagged in https://github.com/CiscoDevNet/ansible-nso",
                "hpe.nimble 1.1.4 is not tagged in https://github.com/hpe-storage/nimble-ansible-modules",
                "inspur.sm 2.3.0 is not tagged in https://github.com/ISIB-Group/inspur.sm",
                "mellanox.onyx 1.0.0 is not tagged in https://github.com/ansible-collections/mellanox.onyx",
            ],
            1,
            id="simple",
        ),
        pytest.param(
            ["-I", "cisco.nso"],
            [
                "hpe.nimble 1.1.4 is not tagged in https://github.com/hpe-storage/nimble-ansible-modules",
                "inspur.sm 2.3.0 is not tagged in https://github.com/ISIB-Group/inspur.sm",
                "mellanox.onyx 1.0.0 is not tagged in https://github.com/ansible-collections/mellanox.onyx",
            ],
            1,
            id="one-ignore",
        ),
        pytest.param(
            ["-I", "cisco.nso", "-I", "xyz"],
            [
                "hpe.nimble 1.1.4 is not tagged in https://github.com/hpe-storage/nimble-ansible-modules",
                "inspur.sm 2.3.0 is not tagged in https://github.com/ISIB-Group/inspur.sm",
                "mellanox.onyx 1.0.0 is not tagged in https://github.com/ansible-collections/mellanox.onyx",
                "invalid ignore 'xyz': xyz does not match any collection",
            ],
            1,
            id="one-ignore-with-invalid",
        ),
        pytest.param(
            [
                "-I",
                "cisco.nso",
                "-I",
                "hpe.nimble",
                "-I",
                "inspur.sm",
                "-I",
                "mellanox.onyx",
            ],
            [],
            0,
            id="ignore-all",
        ),
        pytest.param(
            [
                "-I",
                "cisco.nso",
                "-I",
                "hpe.nimble",
                "-I",
                "inspur.sm",
                "-I",
                "mellanox.onyx",
                "-I",
                "asdf",
                "-I",
                "community.general",
            ],
            [
                "invalid ignore 'asdf': asdf does not match any collection",
                "useless ignore 'community.general':"
                " community.general 6.5.0 is properly tagged",
            ],
            1,
            id="ignore-all-with-invalid",
        ),
    ],
)
def test_validate_tags_file(
    test_data_path: Path,
    capsys: pytest.CaptureFixture,
    args: list[str],
    expected: list[str],
    ret: int,
):
    path = test_data_path / "ansible-7.4.0-tags.yaml"
    assert run(["antsibull-build", "validate-tags-file", str(path), *args]) == ret
    out, err = capsys.readouterr()
    assert sorted(err.splitlines()) == sorted(expected)


@pytest.mark.parametrize(
    "args, ignore_file_contents, expected, ret",
    [
        pytest.param(
            [],
            [],
            [
                "cisco.nso 1.0.3 is not tagged in https://github.com/CiscoDevNet/ansible-nso",
                "hpe.nimble 1.1.4 is not tagged in https://github.com/hpe-storage/nimble-ansible-modules",
                "inspur.sm 2.3.0 is not tagged in https://github.com/ISIB-Group/inspur.sm",
                "mellanox.onyx 1.0.0 is not tagged in https://github.com/ansible-collections/mellanox.onyx",
            ],
            1,
            id="simple",
        ),
        pytest.param(
            [],
            ["cisco.nso"],
            [
                "hpe.nimble 1.1.4 is not tagged in https://github.com/hpe-storage/nimble-ansible-modules",
                "inspur.sm 2.3.0 is not tagged in https://github.com/ISIB-Group/inspur.sm",
                "mellanox.onyx 1.0.0 is not tagged in https://github.com/ansible-collections/mellanox.onyx",
            ],
            1,
            id="one-ignore",
        ),
        pytest.param(
            [],
            ["cisco.nso", "xyz"],
            [
                "hpe.nimble 1.1.4 is not tagged in https://github.com/hpe-storage/nimble-ansible-modules",
                "inspur.sm 2.3.0 is not tagged in https://github.com/ISIB-Group/inspur.sm",
                "mellanox.onyx 1.0.0 is not tagged in https://github.com/ansible-collections/mellanox.onyx",
                "invalid ignore 'xyz': xyz does not match any collection",
            ],
            1,
            id="one-ignore-with-invalid",
        ),
        pytest.param(
            [],
            [
                "cisco.nso",
                "hpe.nimble",
                "inspur.sm",
                "mellanox.onyx",
            ],
            [],
            0,
            id="ignore-all",
        ),
        pytest.param(
            [],
            [
                "cisco.nso",
                "hpe.nimble",
                "inspur.sm",
                "mellanox.onyx",
                "asdf",
            ],
            ["invalid ignore 'asdf': asdf does not match any collection"],
            1,
            id="ignore-all-with-invalid",
        ),
        pytest.param(
            ["-I", "mellanox.onyx", "-I", "xyz"],
            [
                "cisco.nso",
                "hpe.nimble",
                "inspur.sm",
                "asdf",
            ],
            [
                "invalid ignore 'xyz': xyz does not match any collection",
                "invalid ignore 'asdf': asdf does not match any collection",
            ],
            1,
            id="mixed",
        ),
    ],
)
def test_validate_tags_file_ignore_file(
    test_data_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    args: list[str],
    ignore_file_contents: list[str],
    expected: list[str],
    ret: int,
):
    path = test_data_path / "ansible-7.4.0-tags.yaml"
    ignores_file = tmp_path / "ignores_file"
    ignores_file.write_text("\n".join(ignore_file_contents))
    ran = run(
        [
            "antsibull-build",
            "validate-tags-file",
            str(path),
            "--ignores-file",
            str(ignores_file),
            *args,
        ]
    )
    assert ran == ret
    out, err = capsys.readouterr()
    assert sorted(err.splitlines()) == sorted(expected)


def test_validate_tags(test_data_path: Path, tmp_path: Path):
    ignores_file = test_data_path / "validate-tags-ignores"
    name = "ansible-7.4.0-tags.yaml"
    expected_data_path = test_data_path / name
    expected_data = load_yaml_file(expected_data_path)
    output_data_path = tmp_path / name
    with patch(
        "antsibull_build.tagging.get_collections_tags", return_value=expected_data
    ):
        ran = run(
            [
                "antsibull-build",
                "validate-tags",
                f"--data-dir={test_data_path}",
                f"--ignores-file={ignores_file}",
                f"--output={output_data_path}",
                "--error-on-useless-ignores",
                "7.4.0",
            ]
        )
    assert ran == 0
    output_data = load_yaml_file(output_data_path)
    assert expected_data == output_data
