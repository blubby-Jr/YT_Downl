#!/usr/bin/env python3
"""
YouTube Downloader — supports MP4 (video) and MP3 (audio) with quality selection.
Requires: pip install yt-dlp

Config file: yt_downloader.cfg  (created automatically on first run)
"""

import os
import sys
import configparser

try:
    import yt_dlp
except ImportError:
    print("❌  yt-dlp is not installed. Run:  pip install yt-dlp")
    sys.exit(1)


# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "yt_downloader.cfg")

DEFAULT_CONFIG = """\
[ffmpeg]
# Set use_custom_path to true if you want to specify a custom ffmpeg location.
# If false, ffmpeg will be auto-detected from your system PATH.
use_custom_path = false

# Path to the ffmpeg binary or its parent folder.
# Only used when use_custom_path = true.
# Examples:
#   Windows : C:\\ffmpeg\\bin\\ffmpeg.exe
#   Linux   : /usr/local/bin/ffmpeg
#   macOS   : /opt/homebrew/bin/ffmpeg
path =

[output]
# Download folder for MP4 video files.
# Leave blank to be prompted each time (default: ~/Downloads).
mp4_dir =

# Download folder for MP3 audio files.
# Leave blank to be prompted each time (default: ~/Downloads).
mp3_dir =
"""


def ensure_config() -> configparser.ConfigParser:
    """Load config, creating the file with defaults if it doesn't exist."""
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(DEFAULT_CONFIG)
        print(f"  📄  Config file created: {CONFIG_PATH}")
        print("       Edit it to set ffmpeg path and output folders.\n")

    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding="utf-8")

    # Ensure [output] section exists in older configs that predate this feature
    if not cfg.has_section("output"):
        cfg.add_section("output")
        cfg.set("output", "mp4_dir", "")
        cfg.set("output", "mp3_dir", "")
        save_config(cfg)

    return cfg


def save_config(cfg: configparser.ConfigParser):
    """Persist config changes back to disk."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)


def get_ffmpeg_from_config(cfg: configparser.ConfigParser) -> str | None:
    """
    Read ffmpeg settings from config.
    Returns a validated directory path, or None if not configured / disabled.
    """
    use_custom = cfg.getboolean("ffmpeg", "use_custom_path", fallback=False)
    if not use_custom:
        return None

    raw = cfg.get("ffmpeg", "path", fallback="").strip()
    if not raw:
        print("  ⚠   use_custom_path is true but path is empty in config.")
        return None

    raw = os.path.expandvars(os.path.expanduser(raw))

    if os.path.isfile(raw):
        return os.path.dirname(raw)
    if os.path.isdir(raw):
        return raw

    print(f"  ⚠   Config ffmpeg path not found: {raw}")
    return None


def get_output_dir(cfg: configparser.ConfigParser, fmt: str) -> str:
    """
    Resolve the output directory for the given format ('mp4' or 'mp3').
    Priority:
      1. Config value (mp4_dir / mp3_dir) if set and valid
      2. Interactive prompt with ~/Downloads as default
    """
    key         = "mp4_dir" if fmt == "mp4" else "mp3_dir"
    default_dir = os.path.join(os.path.expanduser("~"), "Downloads")

    cfg_raw = cfg.get("output", key, fallback="").strip()
    if cfg_raw:
        expanded = os.path.expandvars(os.path.expanduser(cfg_raw))
        os.makedirs(expanded, exist_ok=True)
        print(f"  ✔  Output folder from config: {expanded}")
        return expanded

    # No config value — ask interactively
    raw = input(f"\n  Output folder [{default_dir}]: ").strip()
    out_dir = os.path.expandvars(os.path.expanduser(raw)) if raw else default_dir
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def prompt_choice(label: str, options: list[str]) -> int:
    """Display a numbered menu and return the 0-based index chosen."""
    print(f"\n{label}")
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt}")
    while True:
        raw = input("  → Your choice: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"  Please enter a number between 1 and {len(options)}.")


def find_ffmpeg() -> str | None:
    """Try to auto-detect ffmpeg on PATH; return its directory or None."""
    import shutil
    exe = shutil.which("ffmpeg")
    return os.path.dirname(exe) if exe else None


def prompt_ffmpeg(cfg: configparser.ConfigParser) -> str | None:
    """
    Resolve the ffmpeg directory with this priority:
      1. Config file (if use_custom_path = true and path is valid)
      2. Interactive prompt (user may save result to config)
      3. Auto-detection from PATH
    """
    cfg_dir = get_ffmpeg_from_config(cfg)
    if cfg_dir:
        exe = os.path.join(cfg_dir, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if os.path.isfile(exe):
            print(f"  ✔  ffmpeg loaded from config: {cfg_dir}")
            return cfg_dir
        print(f"  ⚠   Config path exists but no ffmpeg binary found in: {cfg_dir}")

    auto = find_ffmpeg()
    hint = f"auto-detected: {auto}" if auto else "not found on PATH"
    print(f"\n  ffmpeg ({hint})")
    raw = input("  Custom path (or Enter to use auto / skip): ").strip()

    if not raw:
        if auto:
            print(f"  ✔  Using ffmpeg at: {auto}")
            return auto
        print("  ⚠   ffmpeg not found — MP3 conversion and merging may fail.")
        return None

    raw = os.path.expandvars(os.path.expanduser(raw))
    if os.path.isfile(raw):
        directory = os.path.dirname(raw)
    elif os.path.isdir(raw):
        directory = raw
    else:
        print(f"  ⚠   Path not found: {raw} — proceeding without custom ffmpeg.")
        return None

    exe = os.path.join(directory, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if not os.path.isfile(exe):
        print(f"  ⚠   No ffmpeg binary found in {directory} — proceeding anyway.")
    else:
        print(f"  ✔  Using ffmpeg at: {directory}")

    save = input("  💾  Save this path to config for next time? [y/N]: ").strip().lower()
    if save == "y":
        cfg.set("ffmpeg", "use_custom_path", "true")
        cfg.set("ffmpeg", "path", directory)
        save_config(cfg)
        print(f"  ✔  Saved to {CONFIG_PATH}")

    return directory


def fetch_formats(url: str) -> dict:
    """Return video info without downloading."""
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def progress_hook(d: dict):
    if d["status"] == "downloading":
        pct   = d.get("_percent_str", "?%").strip()
        speed = d.get("_speed_str", "? B/s").strip()
        eta   = d.get("_eta_str", "?").strip()
        print(f"\r  ⬇  {pct}  |  {speed}  |  ETA {eta}   ", end="", flush=True)
    elif d["status"] == "finished":
        print(f"\r  ✅  Download complete: {d['filename']}")


# ──────────────────────────────────────────────
# Download logic
# ──────────────────────────────────────────────

MP4_QUALITIES = {
    "Best available":   "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "1080p":            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
    "720p":             "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
    "480p":             "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
    "360p":             "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best",
    "Worst (smallest)": "worstvideo[ext=mp4]+worstaudio/worst[ext=mp4]/worst",
}

MP3_QUALITIES = {
    "320 kbps (best)": "320",
    "192 kbps":        "192",
    "128 kbps":        "128",
    "96 kbps (small)": "96",
}


def download_mp4(url, quality_label, out_dir, ffmpeg_dir=None):
    fmt = MP4_QUALITIES[quality_label]
    ydl_opts = {
        "format":              fmt,
        "outtmpl":             os.path.join(out_dir, "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
        "progress_hooks":      [progress_hook],
        "quiet":               True,
        "no_warnings":         True,
        "postprocessors": [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
        ],
    }
    if ffmpeg_dir:
        ydl_opts["ffmpeg_location"] = ffmpeg_dir
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_mp3(url, quality_label, out_dir, ffmpeg_dir=None):
    bitrate = MP3_QUALITIES[quality_label]
    ydl_opts = {
        "format":         "bestaudio/best",
        "outtmpl":        os.path.join(out_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "quiet":          True,
        "no_warnings":    True,
        "postprocessors": [
            {
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": bitrate,
            },
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
        "writethumbnail": True,
    }
    if ffmpeg_dir:
        ydl_opts["ffmpeg_location"] = ffmpeg_dir
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


# ──────────────────────────────────────────────
# Main flow
# ──────────────────────────────────────────────

def main():
    clear()
    print("╔══════════════════════════════════════╗")
    print("║   🎬  YouTube Downloader  (yt-dlp)   ║")
    print("╚══════════════════════════════════════╝\n")

    # Load (or create) config
    cfg = ensure_config()

    # 1. URL
    url = input("  Paste YouTube URL: ").strip()
    if not url:
        print("No URL provided. Exiting.")
        sys.exit(0)

    # 2. Fetch title
    print("\n  Fetching video info…", end="", flush=True)
    try:
        info = fetch_formats(url)
    except yt_dlp.utils.DownloadError as e:
        print(f"\n❌  Could not fetch video: {e}")
        sys.exit(1)
    print(f"\r  📺  {info.get('title', 'Unknown title')}")
    duration = info.get("duration_string") or f"{info.get('duration', '?')}s"
    print(f"  ⏱   Duration: {duration}")

    # 3. Format
    fmt_idx = prompt_choice("Select format:", ["MP4 — video", "MP3 — audio only"])
    fmt = "mp4" if fmt_idx == 0 else "mp3"

    # 4. Quality
    if fmt == "mp4":
        quality_labels = list(MP4_QUALITIES.keys())
        q_idx = prompt_choice("Select video quality:", quality_labels)
        quality = quality_labels[q_idx]
    else:
        quality_labels = list(MP3_QUALITIES.keys())
        q_idx = prompt_choice("Select audio bitrate:", quality_labels)
        quality = quality_labels[q_idx]

    # 5. ffmpeg (config → prompt → auto)
    ffmpeg_dir = prompt_ffmpeg(cfg)

    # 6. Output directory (config → prompt)
    out_dir = get_output_dir(cfg, fmt)

    # 7. Download
    print(f"\n  Starting download → {out_dir}\n")
    try:
        if fmt == "mp4":
            download_mp4(url, quality, out_dir, ffmpeg_dir)
        else:
            download_mp3(url, quality, out_dir, ffmpeg_dir)
    except yt_dlp.utils.DownloadError as e:
        print(f"\n❌  Download failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n  Download cancelled.")
        sys.exit(0)

    print(f"\n  Files saved to: {out_dir}")
    print("  Done! 🎉\n")


if __name__ == "__main__":
    main()
