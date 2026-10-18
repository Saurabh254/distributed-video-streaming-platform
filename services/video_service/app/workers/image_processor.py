import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

THUMBNAIL_PRESETS = {
    "large": {"size": (1280, 720), "format": "WEBP", "quality": 85},
    "medium": {"size": (640, 360), "format": "WEBP", "quality": 80},
    "small": {"size": (320, 180), "format": "WEBP", "quality": 75},
    "poster": {"size": (1280, 720), "format": "JPEG", "quality": 90},
}


def extract_video_metadata(video_path: str) -> dict[str, Any]:
    """Extract duration, dimensions, and stream info using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,codec_name:format=duration",
        "-of",
        "json",
        video_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        stream = data.get("streams", [{}])[0] if data.get("streams") else {}
        format_info = data.get("format", {})

        width = stream.get("width")
        height = stream.get("height")
        duration = float(format_info.get("duration", 0.0))

        return {
            "width": int(width) if width else None,
            "height": int(height) if height else None,
            "duration": duration,
            "codec": stream.get("codec_name"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to extract video metadata via ffprobe: %s", exc)
        return {"width": None, "height": None, "duration": 0.0, "codec": None}


def extract_frame_ffmpeg(
    video_path: str,
    output_image_path: str,
    timestamp_sec: float = 0.5,
) -> bool:
    """Extract a single frame from the video at timestamp_sec using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{max(0.0, timestamp_sec):.2f}",
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-update",
        "1",
        "-q:v",
        "2",
        output_image_path,
    ]
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=60,
        )
        if os.path.exists(output_image_path) and os.path.getsize(output_image_path) > 0:
            return True
    except subprocess.CalledProcessError as exc:
        logger.warning(
            "ffmpeg extraction at %ss failed: %s",
            timestamp_sec,
            exc.stderr.decode(errors="ignore"),
        )

    # Fallback to frame 0.0 if timestamp seek failed
    if timestamp_sec > 0.0:
        fallback_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-update",
            "1",
            "-q:v",
            "2",
            output_image_path,
        ]
        try:
            subprocess.run(
                fallback_cmd,
                capture_output=True,
                check=True,
                timeout=60,
            )
            return (
                os.path.exists(output_image_path)
                and os.path.getsize(output_image_path) > 0
            )
        except Exception as fallback_exc:  # noqa: BLE001
            logger.error("ffmpeg fallback extraction failed: %s", fallback_exc)

    return False


def generate_responsive_thumbnails(
    source_image_path: str,
    output_dir: str,
) -> dict[str, str]:
    """
    Process source image with Pillow and generate responsive multi-resolution WebP and JPEG images.
    Returns mapping of variant name to generated local file path.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with Image.open(source_image_path) as img:
        # Convert RGBA/P to RGB for clean WebP and JPEG compression
        if img.mode in ("RGBA", "LA", "P"):
            rgb_img = Image.new("RGB", img.size, (0, 0, 0))
            if img.mode == "P":
                img = img.convert("RGBA")
            rgb_img.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        else:
            rgb_img = img.convert("RGB")

        generated_files: dict[str, str] = {}

        for variant, config in THUMBNAIL_PRESETS.items():
            max_size = config["size"]
            img_format = config["format"]
            quality = config["quality"]
            ext = "webp" if img_format == "WEBP" else "jpg"
            target_filename = f"{variant}.{ext}"
            target_file_path = str(out_path / target_filename)

            # Resize maintaining aspect ratio
            resized = rgb_img.copy()
            resized.thumbnail(max_size, Image.Resampling.LANCZOS)
            resized.save(
                target_file_path,
                format=img_format,
                quality=quality,
                optimize=True,
            )
            generated_files[variant] = target_file_path

        return generated_files
