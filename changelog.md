#### Date: 18-02-2025

Changes:

1. Added a wakeword detection model named "Drama"
2. Used VAD based audio recording, and Open-AI whisper based audio transcription
3. Used custom system instruct (for dramatic response), with llama3.2 running on ollama
4. Added pipeline for chat retention
5. Used Kokoro based tts, from the ollama output

_(The model output is too dramatic, and system instruct might need to be tuned down)_

#### Date: 14-02-2025

Changes: Trained a custom onnx model, for wakeword detection, used microphone detection script to test accuracy (works pretty well!)
