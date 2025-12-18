# app/repositories/history_repo.py
from typing import Dict, List
from threading import Lock

_history: List[Dict] = []
_lock = Lock()

def add_record(record: Dict) -> None:
    with _lock:
        _history.append(record)

def get_all() -> List[Dict]:
    with _lock:
        return list(_history)  # return copy

def clear() -> None:
    with _lock:
        _history.clear()
