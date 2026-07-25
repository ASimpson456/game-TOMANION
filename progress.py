import json
import sys

from paths import app_dir

PROGRESS_PATH = app_dir() / "progress.json"
MAX_LEVEL = 30

DEFAULT = {
    "max_unlocked": 1,
    "current_level": 1,
    "coins": 0,
    "owned": [],
    "equipped": {"tomato": None, "onion": None},
}

_data = None
_dirty = False


def _log_io_error(action, err):
    print(f"progress: {action} failed: {err}", file=sys.stderr)


def _normalize(raw):
    data = {**DEFAULT, **(raw or {})}
    data["max_unlocked"] = max(1, min(MAX_LEVEL, int(data["max_unlocked"])))
    current = int(data["current_level"])
    data["current_level"] = max(1, min(data["max_unlocked"], current))
    data["coins"] = max(0, int(data["coins"]))
    owned = data["owned"]
    data["owned"] = owned if isinstance(owned, list) else []
    equipped = data["equipped"] if isinstance(data["equipped"], dict) else {}
    data["equipped"] = {
        "tomato": equipped.get("tomato"),
        "onion": equipped.get("onion"),
    }
    return data


def _load_from_disk():
    if not PROGRESS_PATH.exists():
        return _normalize({})
    try:
        raw = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        return _normalize(raw if isinstance(raw, dict) else {})
    except (json.JSONDecodeError, OSError) as err:
        _log_io_error("load", err)
        return _normalize({})


def _ensure_loaded():
    global _data
    if _data is None:
        _data = _load_from_disk()
    return _data


def flush():
    global _dirty
    if not _dirty or _data is None:
        return
    try:
        PROGRESS_PATH.write_text(
            json.dumps(_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _dirty = False
    except OSError as err:
        _log_io_error("save", err)


def _touch():
    global _dirty
    _dirty = True


def load_progress():
    return _ensure_loaded()["max_unlocked"]


def load_current_level():
    data = _ensure_loaded()
    return data["current_level"]


def save_progress(max_unlocked):
    data = _ensure_loaded()
    data["max_unlocked"] = max(1, min(MAX_LEVEL, max_unlocked))
    _touch()
    flush()


def save_current_level(level):
    data = _ensure_loaded()
    level = max(1, min(MAX_LEVEL, level))
    data["current_level"] = level
    data["max_unlocked"] = max(data["max_unlocked"], level)
    _touch()
    flush()


def unlock_level(completed_level):
    data = _ensure_loaded()
    data["max_unlocked"] = max(
        data["max_unlocked"],
        min(MAX_LEVEL, completed_level + 1),
    )
    _touch()
    flush()


def reset_levels():
    data = _ensure_loaded()
    data["max_unlocked"] = 1
    data["current_level"] = 1
    _touch()
    flush()


def load_coins():
    return _ensure_loaded()["coins"]


def save_coins(amount):
    data = _ensure_loaded()
    data["coins"] = max(0, int(amount))
    _touch()
    flush()


def add_coins(delta):
    data = _ensure_loaded()
    data["coins"] = max(0, data["coins"] + int(delta))
    _touch()
    return data["coins"]


def load_owned():
    return _ensure_loaded()["owned"]


def load_equipped():
    equipped = _ensure_loaded()["equipped"]
    return {"tomato": equipped["tomato"], "onion": equipped["onion"]}


def purchase_item(item_id, price):
    data = _ensure_loaded()
    owned = data["owned"]
    if item_id in owned:
        return "owned"
    if data["coins"] < price:
        return "nomoney"
    data["coins"] -= price
    owned.append(item_id)
    _touch()
    flush()
    return "ok"


def equip_item(hero, item_id):
    data = _ensure_loaded()
    owned = data["owned"]
    equipped = data["equipped"]
    if item_id is not None:
        if item_id not in owned:
            return False
        item_hero = hero
        for candidate in ("tomato", "onion"):
            if item_id.startswith(candidate + "_"):
                item_hero = candidate
                break
        if item_hero != hero:
            return False
    equipped[hero] = item_id
    _touch()
    flush()
    return True


def toggle_equip(item_id, hero):
    equipped = load_equipped()
    if equipped.get(hero) == item_id:
        return equip_item(hero, None)
    return equip_item(hero, item_id)
