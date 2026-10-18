import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HLS_VARIANTS = [
    {
        "name": "720p",
        "width": 1280,
        "height": 720,
        "video_bitrate": "2800k",
        "maxrate": "2996k",
        "bufsize": "4200k",
        "audio_bitrate": "128k",
        "bandwidth": 2928000,
    },
    {
        "name": "480p",
        "width": 854,
        "height": 480,
        "video_bitrate": "1400k",
        "maxrate": "1498k",
        "bufsize": "2100k",
        "audio_bitrate": "96k",
        "bandwidth": 1496000,
    },
    {
        "name": "360p",
        "width": 640,
        "height": 360,
        "video_bitrate": "800k",
        "maxrate": "856k",
        "bufsize": "1200k",
        "audio_bitrate": "64k",
        "bandwidth": 864000,
    },
]


def transcode_to_hls(
    video_path: str,
    output_dir: str,
    source_height: int | None = None,
    segment_duration: int = 4,
) -> dict[str, Any]:
    """
    Transcode video into multi-variant HLS streams and master playlist.
    Returns dict containing master playlist path, variants generated, and list of all generated files.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Filter variants so we do not upscale lower-resolution source videos
    variants = [
        v for v in HLS_VARIANTS if source_height is None or v["height"] <= source_height
    ]
    if not variants:
        # If source is smaller than 360p, use 360p preset as baseline
        variants = [HLS_VARIANTS[-1]]

    generated_variants: list[str] = []
    master_entries = ["#EXTM3U", "#EXT-X-VERSION:3"]

    for var in variants:
        var_name = var["name"]
        var_dir = out_path / var_name
        var_dir.mkdir(parents=True, exist_ok=True)

        playlist_path = str(var_dir / "index.m3u8")
        segment_pattern = str(var_dir / "segment_%03d.ts")

        w = var["width"]
        h = var["height"]
        v_bitrate = var["video_bitrate"]
        maxrate = var["maxrate"]
        bufsize = var["bufsize"]
        a_bitrate = var["audio_bitrate"]

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            f"scale=w={w}:h={h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            v_bitrate,
            "-maxrate",
            maxrate,
            "-bufsize",
            bufsize,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            a_bitrate,
            "-ar",
            "44100",
            "-hls_time",
            str(segment_duration),
            "-hls_playlist_type",
            "vod",
            "-hls_flags",
            "independent_segments",
            "-hls_segment_filename",
            segment_pattern,
            playlist_path,
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                timeout=300,
            )
        except subprocess.CalledProcessError as exc:
            logger.error(
                "FFmpeg HLS transcode failed for variant %s: %s",
                var_name,
                exc.stderr.decode(errors="ignore"),
            )
            continue

        if os.path.exists(playlist_path):
            generated_variants.append(var_name)
            bw = var["bandwidth"]
            master_entries.append(
                f'#EXT-X-STREAM-INF:BANDWIDTH={bw},RESOLUTION={w}x{h},NAME="{var_name}"'
            )
            master_entries.append(f"{var_name}/index.m3u8")

    if not generated_variants:
        raise RuntimeError("Failed to generate any HLS variant streams")

    # Write master playlist
    master_path = str(out_path / "master.m3u8")
    with open(master_path, "w", encoding="utf-8") as f:
        f.write("\n".join(master_entries) + "\n")

    # Collect all generated files
    all_files: list[tuple[str, str]] = []  # (relative_path, absolute_path)
    for root, _, files in os.walk(output_dir):
        for file in files:
            abs_p = os.path.join(root, file)
            rel_p = os.path.relpath(abs_p, output_dir)
            all_files.append((rel_p, abs_p))

    return {
        "master_playlist_path": master_path,
        "variants": generated_variants,
        "all_files": all_files,
    }
