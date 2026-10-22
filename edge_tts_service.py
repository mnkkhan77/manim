import asyncio
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts
from manim import logger

from manim_voiceover._typing import VoiceoverData
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import PathLike, SpeechService, initialize_speech_service, path_to_string

_sox_mp3_capable = None  # cached per process; see resolve_narration_speed


def _sox_handles_mp3() -> bool:
    """
    Real functional probe, not just `shutil.which("sox")` -- a SoX binary can
    be found on PATH and still fail to actually process mp3s (hit this with
    the ChrisBagwell.SoX winget package's Windows build, which is missing
    libmad; see AGENTS.md). manim_voiceover's global_speed feature needs SoX
    to decode AND re-encode mp3 (edge-tts's output format), so the probe
    round-trips a synthesized clip through both.
    """
    global _sox_mp3_capable
    if _sox_mp3_capable is not None:
        return _sox_mp3_capable

    if shutil.which("sox") is None:
        _sox_mp3_capable = False
        return False

    try:
        with tempfile.TemporaryDirectory() as tmp:
            probe_in = str(Path(tmp) / "probe_in.mp3")
            probe_out = str(Path(tmp) / "probe_out.mp3")
            subprocess.run(
                ["sox", "-n", "-r", "8000", "-c", "1", probe_in, "synth", "0.05", "sine", "440"],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["sox", probe_in, probe_out, "tempo", "1.5"],
                check=True, capture_output=True,
            )
        _sox_mp3_capable = True
    except Exception:
        _sox_mp3_capable = False

    return _sox_mp3_capable


def resolve_narration_speed(requested_speed: float) -> float:
    """
    Returns `requested_speed` as-is if SoX is actually usable, otherwise
    warns and falls back to 1.0 (normal speed) instead of letting
    manim_voiceover's global_speed crash the render with a bare
    FileNotFoundError when SoX is missing or can't handle mp3.
    """
    if requested_speed == 1.0:
        return 1.0
    if _sox_handles_mp3():
        return requested_speed
    print(
        f"narration_speed={requested_speed} requires a working SoX install on PATH "
        "(with mp3 support) -- falling back to 1.0 (normal speed). "
        "See AGENTS.md's Environment section.",
        file=sys.stderr,
    )
    return 1.0


class EdgeTTSService(SpeechService):
    """SpeechService class for Microsoft Edge's online text-to-speech API.
    This is a wrapper around the `edge-tts <https://github.com/rany2/edge-tts>`__
    library, which uses the same neural voices as Microsoft Edge's
    "Read Aloud" feature. No API key is required, and the voices sound
    noticeably more natural than gTTS.

    See ``python -m edge_tts --list-voices`` for all available voices.
    """

    def __init__(self, voice: str = "en-US-AndrewNeural", **kwargs: object) -> None:
        """
        Args:
            voice (str, optional): The edge-tts voice to use. Defaults to
                "en-US-AndrewNeural", a warm, conversational male US English
                neural voice well suited for an interview-style voiceover.
        """
        initialize_speech_service(self, kwargs)
        self.voice = voice

    def generate_from_text(
        self,
        text: str,
        cache_dir: PathLike | None = None,
        path: PathLike | None = None,
        **kwargs: object,
    ) -> VoiceoverData:
        """"""
        if cache_dir is None:
            cache_dir = self.cache_dir

        input_text = remove_bookmarks(text)
        input_data = {"input_text": input_text, "service": "edge-tts", "voice": self.voice}

        cached_result = self.get_cached_result(input_data, cache_dir)
        if cached_result is not None:
            return cached_result

        if path is None:
            audio_path = self.get_audio_basename(input_data) + ".mp3"
        else:
            audio_path = path_to_string(path)

        voice = kwargs.pop("voice", self.voice)
        full_path = str(Path(cache_dir) / audio_path)

        try:
            asyncio.run(self._synthesize(input_text, voice, full_path))
        except Exception as e:
            logger.error(e)
            raise Exception(
                "edge-tts gave an error. You are either not connected to the internet, "
                "or there is a problem with the Microsoft Edge TTS service. "
                f"voice = {voice}."
            )

        json_dict: VoiceoverData = {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
        }

        return json_dict

    @staticmethod
    async def _synthesize(text: str, voice: str, path: str) -> None:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
