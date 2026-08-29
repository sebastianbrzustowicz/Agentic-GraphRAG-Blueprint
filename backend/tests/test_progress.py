from src.progress import (
    file_finished,
    file_started,
    set_error,
    set_result,
    snapshot,
    start,
    stop,
)


def test_start_resets_state():
    start(3, ["a.txt", "b.txt", "c.txt"])
    state = snapshot()
    assert state["running"] is True
    assert state["total_files"] == 3
    assert state["processed_files"] == 0
    assert state["files"] == ["a.txt", "b.txt", "c.txt"]
    assert state["result"] is None
    assert state["error"] is None


def test_file_lifecycle():
    start(2, ["a.txt", "b.txt"])
    file_started("a.txt")
    assert snapshot()["current_file"] == "a.txt"
    file_finished()
    assert snapshot()["processed_files"] == 1
    file_started("b.txt")
    file_finished()
    assert snapshot()["processed_files"] == 2


def test_result_and_error():
    start(1, ["a.txt"])
    set_result({"chunks": 5})
    assert snapshot()["result"] == {"chunks": 5}
    set_error("boom")
    assert snapshot()["error"] == "boom"


def test_stop():
    start(1, ["a.txt"])
    stop()
    assert snapshot()["running"] is False


def test_snapshot_is_a_copy():
    start(1, ["a.txt"])
    state = snapshot()
    state["files"].append("extra.txt")
    assert snapshot()["files"] == ["a.txt"]
