import logging
from dataclasses import dataclass
from pathlib import Path

from relive_dm.dlc import download_dlc
from relive_dm.masters import merge_all_masters
from relive_dm.patch import download_patch

logger = logging.getLogger(__name__)


@dataclass
class ServerInfo:
    name: str
    entry_url: str
    lang_id: int


servers = [
    ServerInfo(
        name="jp_ja",
        entry_url="https://ep.jp.revuestarlight-relive.com/",
        lang_id=1,
    ),
    ServerInfo(
        name="ww_en",
        entry_url="https://ep.ww.revuestarlight-relive.com/",
        lang_id=2,
    ),
]


def download_all(path: Path, patch: bool = True, dlc: bool = True):
    for server in servers:
        logger.info(f"Downloading {server.name}")
        if patch:
            download_patch(server.entry_url, server.lang_id, path / server.name)
        if dlc:
            download_dlc(server.entry_url, server.lang_id, path / server.name)
    if patch:
        merge_all_masters([path / server.name for server in servers], path / "masters")
