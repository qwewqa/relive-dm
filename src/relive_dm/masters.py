import json
import logging
from pathlib import Path
from typing import Any, TypeAlias

logger = logging.getLogger(__name__)

MasterDict: TypeAlias = dict[int, dict[str, Any]]


def merge_values(primary: Any, other: Any) -> Any:
    if isinstance(primary, dict):
        for k, v in other.items():
            if k in primary:
                primary[k] = merge_values(primary[k], v)
            else:
                primary[k] = v
        return primary
    return primary


def merge_masters(primary: MasterDict, other: MasterDict) -> MasterDict:
    for k, v in other.items():
        if k in primary:
            primary[k] = merge_values(primary[k], v)
        else:
            primary[k] = v
    return primary


def correct_arrays(data: MasterDict) -> MasterDict:
    keys = set()
    for v in data.values():
        if not isinstance(v, dict):
            return data
        keys |= set(v.keys())
    for key in keys:
        values = [v[key] for v in data.values() if key in v]
        is_array = True
        for v in values:
            if not (isinstance(v, dict) and all(k.isdigit() for k in v.keys())):
                is_array = False
                break
            indexes = [int(k) for k in v.keys()]
            if indexes and (min(indexes) != 1 or max(indexes) != len(indexes)):
                is_array = False
                break
        if is_array:
            for k, v in data.items():
                if key in v:
                    v[key] = [v[key][str(i)] for i in range(1, len(v[key]) + 1)]
    return data


def get_masters_path(base_path: Path) -> Path:
    return base_path / "src" / "Master" / "Data"


def merge_all_masters(base_paths: list[Path], out_path: Path):
    if len(base_paths) == 0:
        raise ValueError("Must specify at least one base path.")
    primary, *others = [get_masters_path(base_path) for base_path in base_paths]
    for master_path in primary.glob("*.json"):
        data = json.loads(master_path.read_text(encoding="utf-8"))
        for other in others:
            other_path = other / master_path.name
            if other_path.exists():
                data = merge_masters(
                    data, json.loads(other_path.read_text(encoding="utf-8"))
                )
        data = correct_arrays(data)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / master_path.name).write_text(
            json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True),
            encoding="utf-8",
        )
        logger.info(f"Updated {master_path}")
