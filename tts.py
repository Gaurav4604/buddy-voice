import os
import time
import numpy as np
import simpleaudio as sa
import soundfile as sf
import ollama
import torch  # Import torch to detect GPU availability
from kokoro import KPipeline


def play_audio(audio, sample_rate=24000):
    """
    Convert the generated audio (assumed float32, normalized) to 16-bit PCM and play.
    """
    # If audio is a PyTorch tensor, convert it to a NumPy array.
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()

    # Normalize audio to the range [-1, 1] and convert to int16.
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio_norm = audio / max_val
    else:
        audio_norm = audio
    audio_int16 = np.int16(audio_norm * 32767)
    play_obj = sa.play_buffer(audio_int16, 1, 2, sample_rate)
    play_obj.wait_done()


def chat_llm(history, user_input, client, model="llama3.2"):
    """
    Sends the conversation history along with the new user input to the LLM and returns the assistant's reply.
    """
    # Append user input to history.
    history.append({"role": "user", "content": user_input})
    # Query the LLM.
    res = client.chat(model=model, messages=history)
    # Extract the assistant reply (using a default fallback if missing).
    assistant_reply = res.message.get("content", "Sorry, I did not understand that.")
    # Append the assistant reply to the conversation history.
    history.append({"role": "assistant", "content": assistant_reply})
    return assistant_reply


def generate_audio(text, pipeline, voice="af_heart", speed=1, split_pattern=r"\n+"):
    """
    Uses the TTS pipeline to generate audio segments from the given text.
    The text is split using the provided split_pattern (by newline in this case).

    Returns:
        segments (list): A list of tuples (graphemes, phonemes, audio) for each segment.
    """
    generator = pipeline(text, voice=voice, speed=speed, split_pattern=split_pattern)
    segments = list(generator)
    return segments


def play_audio_segments(segments, sample_rate=24000, pause_duration=0.2):
    """
    Plays each audio segment sequentially with a brief pause between segments.

    Args:
        segments (list): List of tuples (graphemes, phonemes, audio).
        sample_rate (int): Audio sample rate.
        pause_duration (float): Pause in seconds between each audio segment.
    """
    for _, _, audio in segments:
        play_audio(audio, sample_rate)
        time.sleep(pause_duration)


def save_audio(audio, save_dir, message_count, sample_rate=24000):
    """
    Saves the generated audio file into the specified directory.
    Returns the filename of the saved audio.
    """
    filename = os.path.join(save_dir, f"reply_segment_{message_count}.wav")
    sf.write(filename, audio, sample_rate)
    return filename


def main():
    # Create "responses" directory if it doesn't exist.
    responses_dir = "responses"
    os.makedirs(responses_dir, exist_ok=True)

    # Detect if a GPU is available.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Initialize the LLM client and the voice generator pipeline with the appropriate device.
    client = ollama.Client()
    # Pass the detected device to the pipeline to ensure GPU acceleration.
    pipeline = KPipeline(
        lang_code="a", device=device
    )  # Ensure lang_code matches your desired voice configuration

    # Conversation history stores all messages (as dict items).
    messages = []
    message_count = 0

    print("Welcome to the interactive LLM + Voice generator interface!")
    print("Type your message and press Enter. Type '/exit' to quit.\n")

    while True:
        # Get user input from the command line.
        user_input = input("You: ").strip()
        if user_input == "/exit":
            print("Exiting the program.")
            break

        # Get the assistant's reply from the LLM.
        assistant_reply = chat_llm(messages, user_input, client)
        message_count += 1

        # Generate audio segments for the assistant's reply.
        segments = generate_audio(assistant_reply, pipeline)

        # Play the generated audio segments.
        print("Playing audio segments...")
        play_audio_segments(segments)

        # Display the assistant's reply.
        print("LLM:", assistant_reply)


if __name__ == "__main__":
    main()
