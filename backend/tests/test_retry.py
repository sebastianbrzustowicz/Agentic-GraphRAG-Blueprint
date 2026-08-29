import pytest
from openai import APIConnectionError, NotFoundError

from src.storage.vector_store import _retry_call


class _FakeRequest:
    def __init__(self) -> None:
        self.headers = {}


class _FakeResponse:
    def __init__(self) -> None:
        self.request = _FakeRequest()
        self.status_code = 404
        self.headers = {"x-request-id": "test"}


def _not_found() -> NotFoundError:
    return NotFoundError("DeploymentNotFound", response=_FakeResponse(), body=None)


def _connection_error() -> APIConnectionError:
    return APIConnectionError(message="connection failed", request=_FakeRequest())


def test_retries_transient_failures_then_succeeds(monkeypatch):
    monkeypatch.setattr("src.storage.vector_store.time.sleep", lambda _: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _not_found()
        return "ok"

    assert _retry_call(flaky, attempts=4, delay=1.0) == "ok"
    assert calls["n"] == 3


def test_retries_other_retryable_errors():
    def flaky():
        raise _connection_error()

    with pytest.raises(APIConnectionError):
        _retry_call(flaky, attempts=3, delay=0.001)


def test_exhausts_attempts_then_raises():
    def always_fails():
        raise _not_found()

    with pytest.raises(NotFoundError):
        _retry_call(always_fails, attempts=3, delay=0.001)


def test_non_retryable_error_propagates_immediately():
    def boom():
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        _retry_call(boom, attempts=4, delay=0.001)
