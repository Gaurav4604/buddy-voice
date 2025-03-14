from src.input_utils import AudioInputProcessor
from src.output_utils import AudioOutputProcessor
from src.llm_utils import LLMProcessor
from src.drama_instruct import DRAMA_SYSTEM_PROMPT
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
    parser.add_argument(
        "--conversation_timeout",
        type=float,
        default=10.0,
        help="Seconds to wait for follow-up speech before returning to wake word mode",
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

    wake_word_required = True

    try:
        while True:
            if wake_word_required and not input_processor.wait_for_wakeword():
                print("Waiting for wake word...")
                continue
            else:
                # conversation loop
                print("Recording speech in conversation mode...")
                recorded_audio = input_processor.record_with_vad(inactivity_sec=2)
                if recorded_audio.size == 0:
                    print("No audio recorded. Ending conversation.")
                    wake_word_required = True
                    continue

                # if data exists, use it to do transcription
                transcript = input_processor.transcribe_audio(recorded_audio)
                if not transcript:
                    print("Empty transcript. Ending conversation.")
                    wake_word_required = True
                    continue

                print(f"User said: '{transcript}'")
                response = llm_processor.chat(transcript)

                if response == "":
                    wake_word_required = True
                    continue

                print(f"Assistant response: '{response}'")
                output_processor.speak_text(response)

                wake_word_required = False

    except KeyboardInterrupt:
        print("User Program Termination")
    finally:
        print("Cleaning up resources...")


if __name__ == "__main__":
    main()
