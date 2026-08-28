import threading

_lock = threading.Lock()
_state = {
    "running": False,
    "total_files": 0,
    "processed_files": 0,
    "current_file": "",
    "files": [],
    "result": None,
    "error": None,
}


def start(total_files: int, files: list[str]) -> None:
    with _lock:
        _state.update(
            running=True,
            total_files=total_files,
            processed_files=0,
            current_file="",
            files=files,
            result=None,
            error=None,
        )


def file_started(filename: str) -> None:
    with _lock:
        _state["current_file"] = filename


def file_finished() -> None:
    with _lock:
        _state["processed_files"] += 1


def set_result(stats: dict) -> None:
    with _lock:
        _state["result"] = stats


def set_error(message: str) -> None:
    with _lock:
        _state["error"] = message


def stop() -> None:
    with _lock:
        _state["running"] = False


def snapshot() -> dict:
    with _lock:
        return dict(_state)
