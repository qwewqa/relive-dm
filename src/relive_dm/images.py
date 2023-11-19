import gzip
import logging
import os
import platform
import shutil
import struct
import subprocess
from io import BytesIO
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

logger = logging.getLogger(__name__)


def pvr_to_png(path: Path, remove_original: bool = True) -> Path | None:
    out_path = path.with_suffix(".png")
    match platform.system():
        case "Windows":
            executable = Path(__file__).parent / "external" / "PVRTexToolCLI.exe"
        case "Linux":
            executable = Path(__file__).parent / "external" / "PVRTexToolCLI"
        case _:
            logger.warning("pvr_to_png is not supported on this platform, skipping")
            return None
    for _ in range(3):
        try:
            # Sometimes this seems to hang, so there's a timeout
            return_code = subprocess.call(
                [
                    f"{executable}",
                    "-ics",
                    "sRGB",
                    "-f",
                    "R8G8B8A8",
                    "-d",
                    out_path,
                    "-i",
                    f"{path}",
                ],
                timeout=60,
            )
            if return_code != 0:
                logger.warning(
                    f"pvr_to_png failed with return code {return_code}, skipping"
                )
                return None
            else:
                logger.info(f"Converted {path} to {out_path}")
                temp_file_path = path.with_stem(f"{path.stem}_Out")
                if temp_file_path.exists():
                    temp_file_path.unlink()
                if remove_original:
                    path.unlink()
                return
        except subprocess.TimeoutExpired:
            logger.debug(f"pvr_to_png timed out, retrying")
    logger.warning(f"pvr_to_png timed out, skipping")
    return None


def try_decompress(f_in, f_out) -> bool:
    with gzip.GzipFile(fileobj=f_in, mode="rb") as gz:
        try:
            shutil.copyfileobj(gz, f_out)
            return True
        except gzip.BadGzipFile:
            return False


keys = [
    b"pucy98uyh7durwz4",
    b"sdeqyztfpi53ywu3",
    b"c3jcfeyc6ibu4i3q",
    b"uxw6x65x3zhtub5g",
    b"87pgvbbvqttbnwde",
    b"qwdqm46jrvwtaic6",
    b"w7f592wnwk35gs2b",
    b"hgpd9jducsuru63q",
    b"bh2xzgvnfa8irjfw",
    b"622jtrktu3nr4g59",
    b"vxbf3xm28bw72x46",
    b"qbep95iqbejf28r6",
    b"fq5q7kadns7c8g3z",
    b"pz42hs44rzds22vu",
    b"q5rnp9p9arkbmhwd",
    b"vy2n96pqpmhu3yn3",
]
ivs = [
    b"y3pmj6uxb4igng4i",
    b"qp9bdt57yrsuzu3x",
    b"3tvrukkkmej5vwzg",
    b"gr343hjed4j5qqki",
    b"hu5njvrrnbgi44ce",
    b"u4pmpv4yyt55dsx6",
    b"n9nkgnhcdpy59e64",
    b"46k6m78nj9qg5zyi",
    b"rut4jkbgbg9miy36",
    b"4awhb8u9xezcsdam",
    b"58a95xv565fwa9jx",
    b"fuz46xu66up2bzmv",
    b"9fs5xkcpx2g4z2g2",
    b"p4acs39gpz7afahp",
    b"6q5hy4z8rh2myf5z",
    b"6xwawjahe2hz2twc",
]


def process_pvr(path: Path, remove_original: bool = True) -> Path | None:
    with path.open("rb+") as f:
        data = f.read()
        if not data:
            return None
        footer = data[-8:]
        if footer.startswith(b"CRPT"):
            key_ind = footer[5]
            key = keys[key_ind]
            iv = ivs[key_ind]
            cipher = Cipher(
                algorithms.AES(key), modes.CBC(iv), backend=default_backend()
            ).decryptor()
            data = cipher.update(data[:128]) + data[128:-8]
        f.seek(0)
        if try_decompress(BytesIO(data), f):
            f.truncate()
    return pvr_to_png(path, remove_original)
