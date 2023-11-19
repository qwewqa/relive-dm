import concurrent.futures
import io
import logging
import multiprocessing
import zipfile
from pathlib import Path
from typing import Callable, Iterable

import httpx

from relive_dm.audio import process_ckb
from relive_dm.images import process_pvr
from relive_dm.lua import process_lua

logger = logging.getLogger(__name__)


def process_file(path: Path):
    logger.debug(f"Extracted {path}")
    match path.suffix:
        case ".pvr":
            process_pvr(path)
        case ".ckb":
            process_ckb(path)
        case ".lua" | ".luac":
            if "Master" in path.parts and "Data" in path.parts:
                process_lua(path)
        case _:
            pass


def download_zip(url: str, base_path: Path, callback: Callable[[Path], None]):
    r = httpx.get(url)
    r.raise_for_status()
    logger.info(f"Downloaded {url}")
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            path = base_path / info.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as f:
                f.write(z.read(info))
            callback(path)


def download_zips(
    urls: Iterable[str],
    base_path: Path,
    max_download_threads: int,
    max_processing_threads: int | None = None,
):
    if max_processing_threads is None:
        max_processing_threads = multiprocessing.cpu_count()
    if max_download_threads > 1:
        with (
            concurrent.futures.ThreadPoolExecutor(
                max_workers=max_processing_threads
            ) as processing_executor,
            concurrent.futures.ThreadPoolExecutor(
                max_workers=max_download_threads
            ) as download_executor,
        ):

            def callback(path: Path):
                processing_executor.submit(process_file, path)

            for url in urls:
                download_executor.submit(download_zip, url, base_path, callback)
    else:
        # Ensure each zip is fully processed before moving on to the next one
        for url in urls:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_processing_threads
            ) as processing_executor:

                def callback(path: Path):
                    processing_executor.submit(process_file, path)

                download_zip(url, base_path, callback)
