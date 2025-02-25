from utils.input_utils import AudioInputProcessor
from utils.output_utils import AudioOutputProcessor
from utils.llm_utils import LLMProcessor
from utils.drama_instruct import DRAMA_SYSTEM_PROMPT
import argparse
import time


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

    try:
        while True:
            # Wait for initial wake word
            print("Waiting for wake word...")
            if not input_processor.wait_for_wakeword():
                continue

            # Enter conversation mode loop
            in_conversation = True
            while in_conversation:
                # Record and transcribe speech
                print("Recording speech in conversation mode...")
                recorded_audio = input_processor.record_with_vad()

                if recorded_audio.size == 0:
                    print("No audio recorded. Ending conversation.")
                    in_conversation = False
                    continue

                transcript = input_processor.transcribe_audio(recorded_audio)
                if not transcript:
                    print("Empty transcript. Ending conversation.")
                    in_conversation = False
                    continue

                print(f"User said: '{transcript}'")

                # Process with LLM
                response = llm_processor.chat(transcript)
                print(f"Assistant response: '{response}'")

                # Speak the response
                output_processor.speak_text(response)

                # Wait for follow-up speech or timeout
                print(
                    f"Waiting {args.conversation_timeout} seconds for follow-up speech..."
                )
                start_wait_time = time.time()

                # Check for voice activity
                follow_up_audio = input_processor.record_with_vad(
                    inactivity_sec=3,
                    pre_speech_buffer_size=3,
                    max_initial_wait=args.conversation_timeout,
                )

                # If no follow-up detected within timeout, exit conversation mode
                if follow_up_audio.size == 0:
                    print("No follow-up speech detected. Returning to wake word mode.")
                    in_conversation = False
                    input_processor.flush_mic_stream()
                else:
                    print("Follow-up speech detected. Continuing conversation...")
                    # Process this recorded audio in the next loop iteration

    except KeyboardInterrupt:
        print("\nExiting by user request.")
    finally:
        print("Cleaning up resources...")


if __name__ == "__main__":
    main()
