import json
import logging
from pathlib import Path
from typing import Any, TypeAlias, cast

from relive_dm.lua import read_lua_table

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


def convert_dicts_to_lists(data: MasterDict) -> MasterDict:
    """Detects dictionaries that should be lists and converts them."""
    keys = set()
    for sv in data.values():
        if not isinstance(sv, dict):
            return data
        keys |= set(sv.keys())
    for sub_key in keys:
        sub_values = [v[sub_key] for v in data.values() if sub_key in v]
        for sv in sub_values:
            if not (
                isinstance(sv, dict)
                and all(isinstance(i, int) for i in sv.keys())
                and min(sv.keys(), default=1) == 1
                and max(sv.keys(), default=0) == len(sv)
            ):
                break
        else:  # no break
            for v in data.values():
                if sub_key in v:
                    v[sub_key] = [v[sub_key][i] for i in range(1, len(v[sub_key]) + 1)]
    return data


def get_masters_path(base_path: Path) -> Path:
    return base_path / "src" / "Master" / "Data"


def merge_all_masters(base_paths: list[Path], out_path: Path):
    if len(base_paths) == 0:
        raise ValueError("Must specify at least one base path.")
    primary, *others = [get_masters_path(base_path) for base_path in base_paths]
    for master_path in primary.glob("*.luac"):
        data = cast(MasterDict, read_lua_table(master_path.read_bytes()))
        for other in others:
            other_path = other / master_path.name
            if other_path.exists():
                data = merge_masters(
                    data, cast(MasterDict, read_lua_table(other_path.read_bytes()))
                )
        data = convert_dicts_to_lists(data)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / f"{master_path.stem}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True),
            encoding="utf-8",
        )
        logger.info(f"Updated {master_path}")
