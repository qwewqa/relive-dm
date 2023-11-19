from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import httpx
import msgpack
from pydantic import BaseModel

from relive_dm.download import download_zips

logger = logging.getLogger(__name__)


def download_dlc(entry_url: str, lang_id: int, base_path: Path):
    config = load_dlc_config(base_path)

    info = get_dlc_info(entry_url, lang_id)
    if info.dlc_ver <= config.version:
        logger.info("No new dlc, skipping")
        return
    download_list = download_dlc_list(info, lang_id)
    logger.info(f"Downloaded dlc list from {info.dlc_server_url}")

    urls = [
        get_dlc_download_url(info.dlc_server_url, lang_id, category, entry)
        for category, entries in download_list.dlc_list.items()
        for entry in entries
        if category not in config.downloaded or entry not in config.downloaded[category]
    ]

    download_zips(urls, base_path, max_download_threads=16)
    logger.info(f"Downloaded {len(urls)} dlc entries")

    save_dlc_config(
        base_path,
        DlcConfig(version=download_list.dlc_ver, downloaded=download_list.dlc_list),
    )


def get_dlc_download_url(
    dlc_server_url: str, lang_id: int, category: str, entry: DlcEntry
) -> str:
    return f"{dlc_server_url}/{lang_id}_{category}_{entry.id}_{entry.version}.zip"


def download_dlc_list(info: DlcInfo, lang_id: int) -> DlcDownloadList:
    r = httpx.get(f"{info.dlc_server_url}/dlc_{info.dlc_ver}_{lang_id}.json")
    r.raise_for_status()
    return DlcDownloadList.model_validate(msgpack.unpackb(r.content))


def load_dlc_config(base_path: Path) -> DlcConfig:
    path = base_path / "dlc_config.json"
    if path.exists():
        return DlcConfig.model_validate_json(path.read_text())
    else:
        return DlcConfig(version=0, downloaded={})


def save_dlc_config(base_path: Path, config: DlcConfig):
    path = base_path / "dlc_config.json"
    path.write_text(config.model_dump_json(indent=4))


def get_dlc_info(entry_url: str, lang_id: int) -> DlcInfo:
    r = httpx.get(f"{entry_url}dlc", params={"lang_id": lang_id})
    r.raise_for_status()
    return DlcInfo.model_validate_json(r.text)


class DlcInfo(BaseModel):
    dlc_ver: int
    dlc_server_url: str


class DlcEntry(NamedTuple):
    id: int
    version: str
    size: int


class DlcDownloadList(BaseModel):
    dlc_ver: int
    dlc_server_url: str
    dlc_list: dict[str, set[DlcEntry]]


class DlcConfig(BaseModel):
    version: int
    downloaded: dict[str, set[DlcEntry]]
