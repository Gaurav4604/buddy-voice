import numpy as np
import pyaudio
import torch
from collections import deque
from openwakeword.model import Model
from faster_whisper import WhisperModel
import threading
import time


class AudioInputProcessor:
    def __init__(
        self, wakeword_model_path="./drama_voice.onnx", whisper_model_size="small"
    ):
        # Audio stream configuration
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1280

        # Initialize PyAudio
        self.audio_interface = pyaudio.PyAudio()
        self.mic_stream = self.audio_interface.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
        )
        self.mic_lock = threading.Lock()

        # Load wakeword detection model
        self.owwModel = Model(
            wakeword_models=[wakeword_model_path], inference_framework="onnx"
        )

        # Load Silero VAD model
        self.vad_model, utils = torch.hub.load("snakers4/silero-vad", "silero_vad")
        (self.get_speech_ts, _, _, _, _) = utils

        # Load Whisper model for transcription
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.whisper_model = WhisperModel(
            whisper_model_size,
            device=self.device,
            compute_type="float16" if self.device == "cuda" else "float32",
        )

    def __del__(self):
        """Clean up resources when object is destroyed"""
        if hasattr(self, "mic_stream") and self.mic_stream is not None:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
        if hasattr(self, "audio_interface") and self.audio_interface is not None:
            self.audio_interface.terminate()

    def flush_mic_stream(self, flush_time=1):
        """Flush the microphone stream by reading and discarding audio"""
        num_chunks = int(self.RATE * flush_time / self.CHUNK)
        print("Flushing microphone stream...")
        for _ in range(num_chunks):
            try:
                with self.mic_lock:
                    self.mic_stream.read(self.CHUNK)
            except Exception as e:
                print(f"Error flushing mic stream: {e}")

    def wait_for_wakeword(self, threshold=0.8):
        """Listen for the wakeword and return when detected"""
        print("Listening for wakewords...")
        while True:
            with self.mic_lock:
                data = self.mic_stream.read(self.CHUNK)
            audio_data = np.frombuffer(data, dtype=np.int16)
            _ = self.owwModel.predict(audio_data)

            # Check if wake word was detected
            wake_detected = False
            for mdl in self.owwModel.prediction_buffer.keys():
                scores = list(self.owwModel.prediction_buffer[mdl])
                if scores and scores[-1] > threshold:
                    wake_detected = True
                    print(f"Wakeword detected! Score: {scores[-1]:.4f}")
                    break

            if wake_detected:
                # Reset the wake word model's internal state
                self.owwModel.reset()
                return True

    def record_with_vad(
        self, inactivity_sec=3, pre_speech_buffer_size=3, max_initial_wait=10
    ):
        """
        Record audio with voice activity detection, only keeping chunks with speech
        and a small buffer of audio before speech starts.

        Args:
            inactivity_sec (int): Seconds of silence before ending recording
            pre_speech_buffer_size (int): Number of chunks to keep before speech starts
            max_initial_wait (float): Maximum seconds to wait for initial speech
        """
        recorded_chunks = []
        audio_buffer = deque(maxlen=20)  # Sliding window for VAD detection
        pre_speech_buffer = deque(
            maxlen=pre_speech_buffer_size
        )  # Buffer to keep some audio before speech

        last_voice_time = (
            None  # Initialize to None, we'll set when first voice is detected
        )
        is_recording = False

        print("Entering VAD mode and listening for speech...")

        # Start timer for initial wait - if no speech detected in initial period, exit
        start_time = time.time()

        while True:
            try:
                with self.mic_lock:
                    data = self.mic_stream.read(self.CHUNK)
            except Exception as e:
                print(f"Error reading microphone in VAD recording: {e}")
                continue

            chunk = np.frombuffer(data, dtype=np.int16)

            # Always keep recent chunks in pre-speech buffer
            pre_speech_buffer.append(chunk)

            # Process for VAD check
            chunk_float = chunk.astype(np.float32) / 32768.0
            audio_buffer.append(chunk_float)
            audio_np = np.concatenate(list(audio_buffer))
            audio_tensor = torch.tensor(audio_np)

            # Check for speech
            speech_timestamps = self.get_speech_ts(
                audio_tensor, self.vad_model, sampling_rate=self.RATE
            )

            if speech_timestamps:
                # If this is the first voice detection
                if not is_recording:
                    is_recording = True
                    print("Voice activity started - recording...")
                    # Add the pre-speech buffer to capture the beginning of speech
                    recorded_chunks.extend(list(pre_speech_buffer))

                # Update last voice time
                last_voice_time = time.time()
                # Add current chunk to recording
                recorded_chunks.append(chunk)

            else:
                # If we're in recording mode, keep recording during small silences
                if is_recording:
                    recorded_chunks.append(chunk)
                    print("Silence detected but still recording.")
                else:
                    print("Waiting for speech...")

                    # Check if we've been waiting too long for initial speech
                    if (
                        time.time() - start_time > max_initial_wait
                    ):  # configurable max wait for initial speech
                        print(
                            f"No initial speech detected for {max_initial_wait} seconds. Ending listening."
                        )
                        return np.array([], dtype=np.int16)

            # Exit if we're recording and silence exceeds threshold
            if is_recording and last_voice_time is not None:
                if time.time() - last_voice_time > inactivity_sec:
                    print(
                        f"No voice activity for {inactivity_sec} seconds. Ending recording."
                    )
                    break

            time.sleep(0.05)

        if not recorded_chunks:
            return np.array([], dtype=np.int16)

        recorded_audio = np.concatenate(recorded_chunks)
        return recorded_audio

    def transcribe_audio(self, audio_data):
        """Transcribe the recorded audio using Whisper"""
        if audio_data.size == 0:
            return ""

        # Normalize the audio for transcription
        audio_float = audio_data.astype(np.float32) / 32768.0

        print("Transcribing recorded audio...")
        segments, _ = self.whisper_model.transcribe(audio_float, beam_size=5)

        # Collect all segment texts
        transcript = []
        for segment in segments:
            transcript.append(segment.text)
            print(f"[{segment.start:.2f}s - {segment.end:.2f}s]: {segment.text}")

        return " ".join(transcript).strip()

    def listen_and_transcribe(self):
        """Complete pipeline: wait for wakeword, record speech, and transcribe"""
        if self.wait_for_wakeword():
            recorded_audio = self.record_with_vad()

            if recorded_audio.size == 0:
                print("No audio recorded. Returning to wakeword detection...")
                return ""

            transcript = self.transcribe_audio(recorded_audio)
            self.flush_mic_stream()
            return transcript

        return ""
