import json

import pytest

from readme_forge.config import (
    ConfigError,
    Options,
    config_to_dict,
    load_config,
    parse_config,
)
from readme_forge.sections import PRESETS
from readme_forge.urls import Instances
from tests.support import FIXTURES, load_json


def test_exported_config_loads():
    config = load_config(FIXTURES / "configs" / "full.json")
    assert config.username == "octocat"
    assert config.options.theme == "dracula"
    assert config.options.typing_lines == ("Ships code; reads docs", "C++ & Objective-C")
    assert config.custom["website"] == "javascript:alert(1)"
    assert config.featured == ("Spoon-Knife", "Hello-World", "does-not-exist")


def test_old_export_without_new_keys_uses_defaults():
    config = parse_config(load_json("configs/full.json"))
    assert config.options.credit is True
    assert config.options.icon_style == "emoji"
    assert config.instances == Instances()


def test_empty_config_defaults_to_classic():
    config = parse_config({})
    assert config.section_ids == PRESETS["classic"]
    assert config.options == Options()


def test_empty_section_list_is_respected():
    assert parse_config({"sections": []}).section_ids == ()


def test_unknown_keys_are_ignored():
    config = parse_config({"options": {"pat": "x", "future": 1}, "extra": True})
    assert config.options == Options()


def test_username_accepts_profile_url():
    assert parse_config({"username": "https://github.com/octocat/"}).username == "octocat"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "JSON object"),
        ({"username": "bad name!"}, "username"),
        ({"sections": ["header", "nope"]}, "unknown section"),
        ({"sections": ["header", "header"]}, "repeat"),
        ({"sections": "header"}, "list of strings"),
        ({"options": {"theme": "neon"}}, "options.theme"),
        ({"options": {"trophyRows": 9}}, "between 1 and 6"),
        ({"options": {"trophyCols": "7"}}, "whole number"),
        ({"options": {"showViews": "yes"}}, "true or false"),
        ({"options": {"iconStyle": "svg"}}, "options.iconStyle"),
        ({"options": {"typingLines": [1]}}, "list of strings"),
        ({"socials": {"twitter": 5}}, "socials.twitter"),
        ({"custom": []}, "custom must be an object"),
        ({"instances": {"stats": "http://x.com"}}, "instance stats"),
        ({"instances": {"nope": "https://x.com"}}, "unknown instance"),
        ({"options": {"bannerText": "x" * 5000}}, "longer than"),
    ],
)
def test_invalid_values_are_rejected(data, message):
    with pytest.raises(ConfigError, match=message):
        parse_config(data)


def test_all_errors_are_reported_together():
    with pytest.raises(ConfigError) as info:
        parse_config({"sections": ["nope"], "options": {"theme": "neon"}})
    assert len(info.value.errors) == 2


def test_config_instances_override_base():
    base = Instances(stats="https://env.example.com")
    config = parse_config({"instances": {"streak": "https://k.example.com"}}, instances=base)
    assert config.instances.stats == "https://env.example.com"
    assert config.instances.streak == "https://k.example.com"


def test_round_trip(tmp_path):
    original = parse_config(load_json("configs/full.json"))
    path = tmp_path / "forge.config.json"
    path.write_text(json.dumps(config_to_dict(original)), encoding="utf-8")
    assert load_config(path) == original


def test_load_config_reports_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="cannot read"):
        load_config(tmp_path / "missing.json")


def test_load_config_reports_bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(path)
