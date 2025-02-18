from utils.input_utils import AudioInputProcessor
from utils.output_utils import AudioOutputProcessor
from utils.llm_utils import LLMProcessor
from utils.drama_instruct import DRAMA_SYSTEM_PROMPT
import argparse


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Voice Interactive Assistant")
    parser.add_argument(
        "--wakeword", default="./drama_voice.onnx", help="Path to wakeword model"
    )
    parser.add_argument(
        "--whisper", default="distil-small.en", help="Whisper model size"
    )
    parser.add_argument("--llm", default="llama3.2", help="LLM model to use")
    parser.add_argument("--voice", default="af_heart", help="TTS voice to use")
    parser.add_argument(
        "--system_prompt",
        default=DRAMA_SYSTEM_PROMPT,
        help="System prompt for the LLM",
    )
    args = parser.parse_args()

    # Initialize processors
    input_processor = AudioInputProcessor(
        wakeword_model_path=args.wakeword, whisper_model_size=args.whisper
    )

    output_processor = AudioOutputProcessor(voice=args.voice)

    llm_processor = LLMProcessor(default_model=args.llm)

    # Add system prompt if provided
    if args.system_prompt:
        llm_processor.add_system_prompt(args.system_prompt)

    print("#" * 100)
    print("Interactive voice assistant initialized!")
    print(f"Say the wake word to begin. Using LLM: {args.llm}, Voice: {args.voice}")
    print("#" * 100)

    try:
        while True:
            # Wait for wake word, record and transcribe
            transcript = input_processor.listen_and_transcribe()

            if not transcript:
                continue

            print(f"User said: '{transcript}'")

            # Process with LLM
            response = llm_processor.chat(transcript)
            print(f"Assistant response: '{response}'")

            # Speak the response
            output_processor.speak_text(response)

    except KeyboardInterrupt:
        print("\nExiting by user request.")
    finally:
        print("Cleaning up resources...")


if __name__ == "__main__":
    main()
