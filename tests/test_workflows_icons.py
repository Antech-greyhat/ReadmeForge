import pytest

from readme_forge.icons import bundled_icon, bundled_licence, recolor, write_icons
from readme_forge.sections import HEADINGS, SECTIONS
from readme_forge.workflows import WORKFLOWS, required_workflows, write_workflows


def test_required_workflows_picks_snake():
    assert [w.file for w in required_workflows(["snake", "header"])] == ["snake.yml"]


def test_required_workflows_follow_section_order():
    files = [w.file for w in required_workflows(["snake", "contrib3d"])]
    assert files == ["profile-3d-contrib.yml", "snake.yml"]


def test_every_workflow_section_has_yaml():
    assert all(WORKFLOWS[s.workflow].yaml for s in SECTIONS if s.workflow)


def test_write_workflows(tmp_path):
    paths = write_workflows(tmp_path / "wf", required_workflows(["snake"]))
    assert paths[0].read_bytes().count(b"\r\n") == 0


@pytest.mark.parametrize("icon", sorted({h.icon for h in HEADINGS.values()}))
def test_every_heading_icon_is_bundled(icon):
    svg = bundled_icon(icon)
    assert svg.lstrip().startswith("<svg")
    assert 'stroke="currentColor"' in svg


def test_recolor():
    assert recolor('<svg stroke="currentColor">', "ABCDEF") == '<svg stroke="#ABCDEF">'


def test_write_icons_deduplicates(tmp_path):
    paths = write_icons(tmp_path, ["star", "star", "link"], "123456")
    assert [p.name for p in paths] == ["star.svg", "link.svg"]
    assert (tmp_path / "icons" / "star.svg").exists()


def test_tabler_licence_is_bundled():
    assert "MIT License" in bundled_licence()
