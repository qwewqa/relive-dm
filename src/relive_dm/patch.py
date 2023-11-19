from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import httpx
from pydantic import BaseModel, Field

from relive_dm.download import download_zips

logger = logging.getLogger(__name__)


def download_patch(entry_url: str, lang_id: int, base_path: Path):
    config = load_patch_config(base_path)
    max_iters = 100
    for _ in range(max_iters):
        r = httpx.get(
            entry_url,
            params={
                "package_type": config.app_config.package_type,
                "app_ver": config.app_config.app_ver_str,
                "lang_id": lang_id,
                "terms_of_service_ver": config.terms_of_service_ver,
                "privacy_policy_ver": config.privacy_policy_ver,
                "maintenance_check": 0,
                "player_id": "nil",
                "super_user_hash": "nil",
                "patch_main_id": config.patch.patch_main_id,
                "patch_main_ver": config.patch.patch_main_ver,
                "patch_main_localize_id": config.patch.patch_main_localize_id,
                "patch_main_localize_ver": config.patch.patch_main_localize_ver,
                "patch_extra_id": config.patch.patch_extra_id,
                "patch_extra_ver": config.patch.patch_extra_ver,
                "patch_extra_localize_id": config.patch.patch_extra_localize_id,
                "patch_extra_localize_ver": config.patch.patch_extra_localize_ver,
            },
        )
        r.raise_for_status()
        data = r.json()
        if "force_update" in data:
            logger.info(
                f"App update required after trying {config.app_config.app_ver_str}"
            )
            config.app_config.app_ver = (
                config.app_config.app_ver[0],
                config.app_config.app_ver[1],
                config.app_config.app_ver[2] + 1,
            )
        elif "terms_of_service_ver" in data:
            logger.info(
                f"Terms of service update to version {data['terms_of_service_ver']}"
            )
            config.terms_of_service_ver = data["terms_of_service_ver"]
        elif "privacy_policy_ver" in data:
            logger.info(
                f"Privacy policy update to version {data['privacy_policy_ver']}"
            )
            config.privacy_policy_ver = data["privacy_policy_ver"]
        elif "patch_server_url" in data:
            download_list = PatchDownloadList.model_validate(data)
            logger.info("Downloaded patch list")

            urls = []
            urls.extend(
                f"{download_list.patch_server_url}/{entry.file_name(0)}"
                for entry in download_list.patch_main
            )
            urls.extend(
                f"{download_list.patch_server_url}/{entry.file_name(lang_id)}"
                for entry in download_list.patch_main_localize
            )
            urls.extend(
                f"{download_list.patch_server_url}/{entry.file_name(0)}"
                for entry in download_list.patch_extra
            )
            urls.extend(
                f"{download_list.patch_server_url}/{entry.file_name(lang_id)}"
                for entry in download_list.patch_extra_localize
            )

            download_zips(urls, base_path, max_download_threads=-1)
            logger.info(f"Downloaded {len(urls)} patch entries")
            if download_list.patch_main:
                config.patch.patch_main_id = download_list.patch_main[-1].id
                config.patch.patch_main_ver = download_list.patch_main[-1].version
            if download_list.patch_main_localize:
                config.patch.patch_main_localize_id = download_list.patch_main_localize[
                    -1
                ].id
                config.patch.patch_main_localize_ver = (
                    download_list.patch_main_localize[-1].version
                )
            if download_list.patch_extra:
                config.patch.patch_extra_id = download_list.patch_extra[-1].id
                config.patch.patch_extra_ver = download_list.patch_extra[-1].version
            if download_list.patch_extra_localize:
                config.patch.patch_extra_localize_id = (
                    download_list.patch_extra_localize[-1].id
                )
                config.patch.patch_extra_localize_ver = (
                    download_list.patch_extra_localize[-1].version
                )
            save_patch_config(base_path, config)
            return
        elif "information_news_url" in data:
            logger.info("No updates available")
            return
        else:
            raise ValueError("Unknown response")
    logger.error(f"Failed to download patch list from {entry_url}")
    raise RuntimeError("Failed to download patch list")


def load_patch_config(base_path: Path) -> PathConfig:
    path = base_path / "patch_config.json"
    if path.exists():
        return PathConfig.model_validate_json(path.read_text())
    else:
        return PathConfig(
            app_config=AppConfig(),
            patch=PatchVersion(),
            terms_of_service_ver=0,
            privacy_policy_ver=0,
        )


def save_patch_config(base_path: Path, config: PathConfig):
    path = base_path / "patch_config.json"
    path.write_text(config.model_dump_json(indent=4))


class AppConfig(BaseModel):
    package_type: int = 3
    app_ver: tuple[int, int, int] = (1, 0, 50)

    @property
    def app_ver_str(self) -> str:
        return ".".join(map(str, self.app_ver))


class PatchVersion(BaseModel):
    patch_main_id: int = 0
    patch_main_ver: str = "a"
    patch_main_localize_id: int = 0
    patch_main_localize_ver: str = "a"
    patch_extra_id: int = 0
    patch_extra_ver: str = "a"
    patch_extra_localize_id: int = 0
    patch_extra_localize_ver: str = "a"


class PathConfig(BaseModel):
    app_config: AppConfig
    patch: PatchVersion
    terms_of_service_ver: int
    privacy_policy_ver: int


class PatchEntry(NamedTuple):
    id: int
    group_id: int
    type: int
    version: str
    size: int

    def file_name(self, lang_id: int) -> str:
        return f"{self.id}_{lang_id}_{self.group_id}_{self.type}_{self.version}.zip"


class PatchDownloadList(BaseModel):
    patch_main: list[PatchEntry] = Field(default_factory=list)
    patch_main_localize: list[PatchEntry] = Field(default_factory=list)
    patch_extra: list[PatchEntry] = Field(default_factory=list)
    patch_extra_localize: list[PatchEntry] = Field(default_factory=list)
    patch_server_url: str
