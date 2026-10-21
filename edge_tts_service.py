import asyncio
from pathlib import Path

import edge_tts
from manim import logger

from manim_voiceover._typing import VoiceoverData
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import PathLike, SpeechService, initialize_speech_service, path_to_string


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
