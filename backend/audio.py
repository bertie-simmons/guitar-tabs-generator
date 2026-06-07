import subprocess
from pathlib import Path

class AudioExtractionError(Exception):
    """Exception raised when audio extraction fails with ffmpeg"""

    def __init__(self, message="ffmpeg error"):
        super().__init__(f"Audio extraction failed: {message}")


def extract_audio(video_path: Path, output_path: Path) -> None:
    """Extract mono 22050Hz WAV from video. Raises AudioExtractionError on failure."""

    if not video_path.exists():
        raise AudioExtractionError(f"Input file not found: {video_path}")
        
    try:
        subprocess.run([
            "ffmpeg",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "22050",
            "-ac", "1",
            str(output_path)
        ], check=True, capture_output=True, text=True)
        print("Audio extracted successfully")
    except subprocess.CalledProcessError as e:
        raise AudioExtractionError(e) from e
    

if __name__ == "__main__":
    video_path = Path("./tests/fixtures/video.mp4")
    output_path = Path("./tests/fixtures/output.wav")

    extract_audio(video_path, output_path)