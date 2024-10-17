import logging
import platform
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def wav_to_opus(path: Path) -> Path | None:
    match platform.system():
        case "Windows":
            executable = Path(__file__).parent / "external" / "ffmpeg.exe"
        case "Linux":
            executable = Path(__file__).parent / "external" / "ffmpeg"
        case _:
            logger.warning("wav_to_opus is not supported on this platform, skipping")
            return None
    out_path = path.with_suffix(".opus")
    result = subprocess.run(
        [
            f"{executable}",
            "-y",
            "-i",
            f"{path}",
            "-c:a",
            "libopus",
            "-b:a",
            "128k",
            f"{out_path}",
        ],
    )
    if result.returncode == 0:
        logger.info(f"Converted {path} to {out_path}")
        return out_path
    else:
        logger.warning(f"Failed to convert {path}")
        return None


def process_ckb(path: Path, remove_original: bool = False) -> Path | None:
    match platform.system():
        case "Windows":
            executable = Path(__file__).parent / "external" / "cktool.exe"
        case "Linux":
            executable = Path(__file__).parent / "external" / "cktool"
        case _:
            logger.warning("ckb_to_wav is not supported on this platform, skipping")
            return None
    result = subprocess.run(
        [
            f"{executable}",
            "extract",
            f"{path}",
        ],
        capture_output=True,
    )
    match = re.search(
        r"writing (.+\.wav)",
        result.stdout.decode("utf-8"),
    )
    if match:
        original_out_path = Path(match.group(1))
        wav_path = path.with_suffix(".wav")
        original_out_path.rename(wav_path)
        opus_path = wav_to_opus(wav_path)
        wav_path.unlink()
        if opus_path:
            logger.info(f"Converted {path} to {opus_path}")
            if remove_original:
                path.unlink()
            return opus_path
        else:
            logger.warning(f"Failed to convert {path}")
            return None
    else:
        logger.warning(f"Failed to convert {path}")
        return None
