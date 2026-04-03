from __future__ import annotations

import json
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from types import NoneType, UnionType
from typing import Any, Literal, Union, get_args, get_origin

from meetings_data import Meeting


def restore_cached_value(value: Any, annotation: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(annotation)

    if origin in (Union, UnionType):
        union_args = [arg for arg in get_args(annotation) if arg is not NoneType]
        if len(union_args) == 1:
            return restore_cached_value(value, union_args[0])
        return value

    if origin is list:
        item_type = get_args(annotation)[0] if get_args(annotation) else Any
        if not isinstance(value, list):
            return []
        return [restore_cached_value(item, item_type) for item in value]

    if origin is dict:
        _, value_type = get_args(annotation) if get_args(annotation) else (Any, Any)
        if not isinstance(value, dict):
            return {}
        return {
            str(key): restore_cached_value(item, value_type)
            for key, item in value.items()
        }

    if origin is Literal:
        return value

    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, dict):
            return value
        restored_data = {
            field.name: restore_cached_value(value[field.name], field.type)
            for field in fields(annotation)
            if field.name in value
        }
        return annotation(**restored_data)

    return value


def load_meetings_cache(cache_path: str) -> list[Meeting]:
    path = Path(cache_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Cache file not found: {cache_path}. Disable local data to fetch fresh meetings."
        )

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError(f"Cache file is invalid: {cache_path}")

    meetings: list[Meeting] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if "meeting_id" in item:
            meetings.append(restore_cached_value(item, Meeting))
        else:
            meetings.append(Meeting.from_dict(item))
    return meetings


def save_meetings_cache(cache_path: str, meetings: list[Meeting]):
    path = Path(cache_path)
    payload = [asdict(meeting) for meeting in meetings]
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")
