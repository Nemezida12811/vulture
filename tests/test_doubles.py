"""Tests for ``ignore_files`` that use test doubles (stub, mock, spy, fake)."""

from pathlib import Path
from unittest import mock

import pytest

from vulture.core import Vulture, main
from vulture.utils import ExitCode


# FAKE
class FakeProject:
    def __init__(self, files):
        self.files = files  # {"/proj/lib.py": "def f(): ..."}

    def scan_into(self, vulture):
        for name, source in self.files.items():
            vulture.scan(source, filename=name)


def reported_names(vulture):
    return sorted(item.name for item in vulture.get_unused_code())


def test_fake_project_ignored_file_is_scanned_but_not_reported():
    project = FakeProject(
        {
            "/proj/lib.py": "def helper(): pass\ndef really_dead(): pass\n",
            "/proj/migrations/m1.py": (
                "from lib import helper\n"
                "helper()\n"
                "def migrate_unused(): pass\n"
            ),
        }
    )
    v = Vulture()
    v.ignore_files = ["*/migrations/*"]  # noqa: V101
    project.scan_into(v)

    # helper() is used from the ignored file -> not reported (scanned).
    # migrate_unused lives in the ignored file -> not reported (ignored).
    assert reported_names(v) == ["really_dead"]


def test_fake_project_without_ignore_files_reports_everything():
    project = FakeProject({"/proj/m1.py": "def unused(): pass\n"})
    v = Vulture()
    project.scan_into(v)
    assert reported_names(v) == ["unused"]


# STUB
@pytest.mark.parametrize(
    "canned_answer, expected",
    [(True, []), (False, ["unused"])],
)
def test_stub_is_ignored_file_controls_report(canned_answer, expected):
    v = Vulture()
    v.scan("def unused(): pass\n", filename="whatever.py")
    with mock.patch.object(
        Vulture, "_is_ignored_file", return_value=canned_answer
    ):
        assert reported_names(v) == expected


# MOCK
def test_main_passes_ignore_files_to_scavenge():
    config = {
        "verbose": False,
        "ignore_names": [],
        "ignore_decorators": [],
        "paths": ["src"],
        "exclude": ["skip_me.py"],
        "ignore_files": ["generated.py", "*/migrations/*"],
        "min_confidence": 0,
        "sort_by_size": False,
        "make_whitelist": False,
    }
    with (
        mock.patch("vulture.core.make_config", return_value=config),  # stub
        mock.patch.object(Vulture, "scavenge") as scavenge,  # mock
        mock.patch.object(
            Vulture, "report", return_value=ExitCode.NoDeadCode
        ),  # stub
        pytest.raises(SystemExit) as excinfo,
    ):
        main()

    scavenge.assert_called_once_with(
        ["src"],
        exclude=["skip_me.py"],
        ignore_files=["generated.py", "*/migrations/*"],
    )
    assert excinfo.value.code == ExitCode.NoDeadCode
