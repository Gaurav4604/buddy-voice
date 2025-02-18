I'll update the README to provide a more comprehensive explanation of the code and how the system works.

# Buddy Voice

A voice-based AI assistant that leverages:

1. Wakeword detection to start listening
2. Voice Activity Detection (VAD) to automatically stop recording when you finish speaking
3. OpenAI-Whisper for accurate voice transcription
4. LLM backend for generating intelligent responses
5. Text-to-Speech (TTS) for natural-sounding replies

## Setup and Installation

### Virtual Environment Setup and Activation

```bash
# Create a virtual environment
python -m venv buddy-voice

# Activate the virtual environment
# On Windows:
./buddy-voice/Scripts/activate
# On macOS/Linux:
source buddy-voice/bin/activate
```

### Package Installation

```bash
# Install required dependencies
pip install -r requirements.txt

# Download necessary model files
python download.py
```

### Usage

```bash
# Run with default settings
python main.py

# Run with custom parameters
python main.py --wakeword "./custom_wakeword.onnx" --whisper "turbo" --llm "deepseek-r1" --system_prompt "I am deepseek, your personal assistant"
```

## How It Works

The system operates through four main components:

1. **Audio Input Processing (`AudioInputProcessor`)**:

   - Listens for a specific wake word using the provided ONNX model
   - Once activated, records audio until silence is detected (Voice Activity Detection)
   - Transcribes the recorded speech using the Whisper model

2. **LLM Processing (`LLMProcessor`)**:

   - Takes transcribed text as input
   - Processes the input through the specified LLM model (default: llama3.2)
   - Generates contextually appropriate responses
   - Maintains conversation history for context-aware interactions

3. **Audio Output Processing (`AudioOutputProcessor`)**:

   - Converts text responses to speech using the kokkoro
   - Handles audio playback of the generated speech

4. **Main Loop**:
   - Continuously listens for the wake word
   - Records, transcribes, and processes user speech
   - Generates and speaks responses
   - Repeats until interrupted

## Command Line Arguments

- `--wakeword`: Path to the wake word detection model (default: "./drama_voice.onnx")
- `--whisper`: Whisper model size to use for transcription (default: "distil-small.en")
- `--llm`: Language model to use for response generation (default: "llama3.2")
- `--voice`: TTS voice model to use for spoken responses (default: "af_heart")
- `--system_prompt`: Custom system prompt for the LLM

## Requirements

The `requirements.txt` file includes all necessary dependencies for:

- Wake word detection
- Audio recording and playback
- Speech-to-text and text-to-speech conversion
- LLM integration

## Note

Make sure your microphone is properly configured before running the application. The system will continuously listen for the wake word, so ensure you're in a relatively quiet environment for optimal performance.
