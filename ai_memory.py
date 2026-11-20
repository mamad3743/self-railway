"""حافظه‌ی مکالمه‌ی محلی و قابل پاک‌سازی برای AI Center."""
import json, os, tempfile, threading

_PATH = os.getenv("AI_MEMORY_FILE", "/data/ai_memory.json")
_LOCK = threading.RLock()
_MAX_TURNS = max(2, min(30, int(os.getenv("AI_MEMORY_TURNS", "8"))))

def _read():
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}

def _write(data):
    folder = os.path.dirname(_PATH) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".ai-memory-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _PATH)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

def history(key):
    with _LOCK:
        rows = _read().get(str(key), [])
        return rows[-(_MAX_TURNS * 2):] if isinstance(rows, list) else []

def remember(key, user, assistant):
    with _LOCK:
        data = _read()
        rows = data.get(str(key), [])
        if not isinstance(rows, list):
            rows = []
        rows.extend([{"role": "user", "content": str(user)[:8000]},
                     {"role": "assistant", "content": str(assistant)[:12000]}])
        data[str(key)] = rows[-(_MAX_TURNS * 2):]
        _write(data)

def clear(key):
    with _LOCK:
        data = _read()
        existed = str(key) in data
        data.pop(str(key), None)
        _write(data)
        return existed

def clear_all():
    with _LOCK:
        _write({})
