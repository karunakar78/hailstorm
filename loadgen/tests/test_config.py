import pytest
from pydantic import ValidationError

from loadgen.config import EngineConfig, load_config

SAMPLE = """
target:
  url: "http://localhost:8000/test"
  method: "get"
  headers: {"X-Test": "1"}
load:
  duration: 30
  rate: 10
  concurrency: 5
request:
  timeout: 5
"""


def test_load_config_roundtrip(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(SAMPLE)
    config = load_config(path)
    assert config.target.url == "http://localhost:8000/test"
    assert config.target.method == "GET"
    assert config.target.headers == {"X-Test": "1"}
    assert config.load.duration == 30
    assert config.load.rate == 10
    assert config.load.concurrency == 5
    assert config.request.timeout == 5


def test_default_request_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(SAMPLE.replace("request:\n  timeout: 5\n", ""))
    config = load_config(path)
    assert config.request.timeout == 5.0


def test_invalid_config_rejected():
    with pytest.raises(ValidationError):
        EngineConfig.model_validate(
            {"target": {"url": "http://x"}, "load": {"duration": -1, "rate": 0, "concurrency": 0}}
        )
