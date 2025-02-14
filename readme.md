# Buddy Voice

A voice based AI assistant, which uses

1. Wakeword detection based transcript recording
2. Voice Activtiy based Recording Termination
3. OpenAI-Whisper based Voice Transcription
4. LLM Backend based Response

## Setup and Installation

### virtual env setup and activation

```bash
python -m venv buddy-voice

./buddy-voice/Scripts/activate
```

### packages installation (temp, will be moved to requirements.txt)

```bash
pip install openwakeword pyaudio

python download.py
```

### Usage

```bash
python detect_from_microphone.py --model_path ./buddy_voice.onnx
```
