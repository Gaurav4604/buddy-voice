import os
import time
import numpy as np
import simpleaudio as sa
import soundfile as sf
import torch
from kokoro import KPipeline


class AudioOutputProcessor:
    def __init__(self, sample_rate=24000, voice="af_heart"):
        # Detect device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device for TTS: {self.device}")

        # Initialize TTS pipeline
        self.pipeline = KPipeline(lang_code="a", device=self.device)

        # Settings
        self.sample_rate = sample_rate
        self.default_voice = voice

        # Message counter for unique filenames
        self.message_count = 0

    def generate_audio(self, text, voice=None, speed=1, split_pattern=r"\n+"):
        """Generate audio segments from the given text"""
        if not text:
            return []

        voice = voice or self.default_voice
        generator = self.pipeline(
            text, voice=voice, speed=speed, split_pattern=split_pattern
        )
        return list(generator)

    def play_audio(self, audio):
        """Play a single audio segment"""
        # If audio is a PyTorch tensor, convert it to a NumPy array
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()

        # Normalize audio to the range [-1, 1] and convert to int16
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio_norm = audio / max_val
        else:
            audio_norm = audio

        audio_int16 = np.int16(audio_norm * 32767)
        play_obj = sa.play_buffer(audio_int16, 1, 2, self.sample_rate)
        play_obj.wait_done()

    def play_audio_segments(self, segments, pause_duration=0.1):
        """Play all audio segments with a pause between them"""
        if not segments:
            print("No audio segments to play")
            return

        for _, _, audio in segments:
            self.play_audio(audio)
            time.sleep(pause_duration)

    def save_audio(self, audio, filename=None):
        """Save audio to file"""
        if filename is None:
            self.message_count += 1
            filename = os.path.join(
                self.responses_dir, f"reply_segment_{self.message_count}.wav"
            )

        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()

        sf.write(filename, audio, self.sample_rate)
        return filename

    def save_audio_segments(self, segments):
        """Save all audio segments to files"""
        filenames = []
        for i, (_, _, audio) in enumerate(segments):
            self.message_count += 1
            filename = os.path.join(
                self.responses_dir, f"reply_segment_{self.message_count}_{i+1}.wav"
            )
            self.save_audio(audio, filename)
            filenames.append(filename)
        return filenames

    def speak_text(self, text, voice=None, speed=1, save=False):
        """Complete pipeline: generate, play, and optionally save audio for text"""
        segments = self.generate_audio(text, voice, speed)
        self.play_audio_segments(segments)

        if save:
            return self.save_audio_segments(segments)
        return None
