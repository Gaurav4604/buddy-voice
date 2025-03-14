import os
import time
import subprocess
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL
import vlc
import cv2
import time
import ollama
from ollama import Client
from pydantic import BaseModel


class ImageDescription(BaseModel):
    description: str


def regenerate_vlc_cache():
    """
    Programmatically regenerates the VLC plugins cache by calling the
    'vlc-cache-gen.exe' command with the plugins directory.
    """
    vlc_path = r"C:\Program Files\VideoLAN\VLC"
    cache_gen_exe = os.path.join(vlc_path, "vlc-cache-gen.exe")
    plugins_dir = os.path.join(vlc_path, "plugins")

    # Build the command; note that the command must be run as administrator.
    cmd = f'"{cache_gen_exe}" "{plugins_dir}"'
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("VLC plugins cache regenerated successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to regenerate VLC plugins cache:", e)


# Regenerate VLC plugins cache before proceeding
regenerate_vlc_cache()

# Ensure VLC’s DLLs are found
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")


ytmusic = YTMusic("browser.json")

# Options for yt-dlp to extract the best audio stream without downloading
ydl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "skip_download": True,
}

# Initialize VLC instance and media player
vlc_instance = vlc.Instance()
player = vlc_instance.media_player_new()


def play_music(query: str) -> None:
    """
    Search for the song user has requested, and play the first result.
    """
    # Search for songs; adjust filter/limit as needed
    results = ytmusic.search(query, filter="songs", limit=1)
    if not results:
        print(f"No track found for query: {query}")
        return

    track = results[0]
    video_id = track.get("videoId")
    if not video_id:
        print("No video ID found in the search result.")
        return

    # Build the YouTube URL for the track
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Use yt-dlp to get stream information (without downloading)
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        stream_url = info.get("url")

    title = track.get("title", "Unknown Title")
    print(f"Now playing: {title}")

    # Create a new VLC media from the stream URL and play it
    media = vlc_instance.media_new(stream_url)
    player.set_media(media)
    player.play()

    # Allow VLC time to start playback
    time.sleep(2)

    # Wait until playback is finished
    while True:
        try:
            state = player.get_state()
            if state == vlc.State.Ended:
                print("Playback finished.")
                break
            elif state == vlc.State.Error:
                print("Error during playback.")
                break
            time.sleep(1)
        except KeyboardInterrupt:
            player.stop()
            print("User Terminate")
            break


def capture_image_and_describe() -> str:
    """
    Use the front-facing camera to capture an image,
    and describe what the image contains
    """
    # Open the default camera (device 0)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise Exception("Could not open video device")

    countdown = 5  # seconds
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue  # Skip if frame read fails

        # Calculate remaining time for the countdown
        elapsed = time.time() - start_time
        remaining = max(int(countdown - elapsed) + 1, 0)

        # Overlay the countdown timer on the frame
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            frame, f"{remaining}", (50, 50), font, 1.5, (0, 0, 255), 4, cv2.LINE_AA
        )

        # Show the camera preview window
        cv2.imshow("Camera Preview", frame)

        # When countdown is complete, capture the image
        if elapsed >= countdown:
            # Optionally wait a tiny bit for a final frame update
            time.sleep(0.1)
            ret, frame = cap.read()
            if not ret:
                continue
            cv2.imwrite("temp.jpg", frame)
            break

        # Allow early exit by pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            return "Cancelled by user"

    # Release the camera and close the preview window
    cap.release()
    cv2.destroyAllWindows()

    # Send the captured image to Ollama for description
    res = ollama.chat(
        model="gemma3",
        messages=[
            {
                "role": "user",
                "content": "describe what is present in this image in 2 lines",
                "images": ["temp.jpg"],
            }
        ],
        options={"temperature": 0},
        format=ImageDescription.model_json_schema(),
    )

    image_description = ImageDescription.model_validate_json(
        res.message.content
    ).description

    # Delete the temporary image file
    if os.path.exists("temp.jpg"):
        os.remove("temp.jpg")

    return f"The Image captured, has a description :{image_description}"


# Example usage:
if __name__ == "__main__":
    # print(ytmusic.get_account_info())
    # while True:
    #     search_term = input("Enter a song to search for (or type 'exit' to quit): ")
    #     if search_term.lower() == "exit":
    #         break
    #     play_music(search_term)
    print(capture_image_and_describe(""))
