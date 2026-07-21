"""静止画(リールフレーム)＋ナレーション音声をffmpegで1本の動画(mp4)に合成する。

Instagram Reels APIがReelsタブ掲載対象と認識するには9:16・5〜90秒である必要があるため、
呼び出し側(main.py)はこの尺がその範囲に収まることを前提にしている
（ナレーション文が極端に短い場合は呼び出し側で長さをチェックすること）。
"""
import glob
import shutil
import subprocess
from pathlib import Path

_FFMPEG_CANDIDATES = [
    # Windows（ローカルのdry-run用。winget install Gyan.FFmpeg でインストールした場合の既定パス）
    str(Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        "/ffmpeg-*/bin/ffmpeg.exe"),
]


def _find_ffmpeg() -> str:
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    for pattern in _FFMPEG_CANDIDATES:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    raise RuntimeError(
        "ffmpegが見つかりません。GitHub Actions(ubuntu-latest)には標準で入っていますが、"
        "ローカルWindowsでは `winget install Gyan.FFmpeg` 等でインストールしてください。"
    )


def compose_reel_video(frame_path: Path, audio_path: Path, out_path: Path) -> Path:
    ffmpeg = _find_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-loop", "1", "-i", str(frame_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-vf", "scale=1080:1920",
        "-movflags", "+faststart",
        "-shortest",
        str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {res.returncode}): {res.stderr[-2000:]}")
    return out_path
