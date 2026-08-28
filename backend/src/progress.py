import threading

_lock = threading.Lock()
_state = {
    "running": False,
    "total_files": 0,
    "processed_files": 0,
    "current_file": "",
}


def start(total_files: int) -> None:
    with _lock:
        _state["running"] = True
        _state["total_files"] = total_files
        _state["processed_files"] = 0
        _state["current_file"] = ""


def file_started(filename: str) -> None:
    with _lock:
        _state["current_file"] = filename


def file_finished() -> None:
    with _lock:
        _state["processed_files"] += 1


def stop() -> None:
    with _lock:
        _state["running"] = False


def snapshot() -> dict:
    with _lock:
        return dict(_state)
