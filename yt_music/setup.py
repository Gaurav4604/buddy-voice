import os
import time
import json
import threading
from ytmusicapi import YTMusic, OAuthCredentials
from yt_dlp import YoutubeDL
import vlc


# Load environment variables and setup OAuth credentials
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")

ytmusic = YTMusic(
    "oauth.json",
    oauth_credentials=OAuthCredentials(
        client_id=client_id, client_secret=client_secret
    ),
)

# Fetch the playlist data
playlist = ytmusic.get_playlist(playlistId="PLWRcTUke7QDaq-6AAntfYrSlfsS2gVAua")
tracks = playlist.get("tracks", [])

# Set up yt_dlp options to extract audio stream URLs without downloading
ydl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "skip_download": True,
}

# Initialize VLC player instance (we will create a new media for each track)
instance = vlc.Instance()
player = instance.media_player_new()

# Global control flags and track index
skip_next = False
skip_prev = False
quit_flag = False
current_index = 0


# This thread continuously reads user input to update the flags.
def input_thread():
    global skip_next, skip_prev, quit_flag
    while not quit_flag:
        command = input("Press [n]ext, [p]revious, or [q]uit: ").strip().lower()
        if command == "n":
            skip_next = True
        elif command == "p":
            skip_prev = True
        elif command == "q":
            quit_flag = True


# Start the input-monitoring thread (as a daemon so it doesn't block exit)
threading.Thread(target=input_thread, daemon=True).start()

while 0 <= current_index < len(tracks) and not quit_flag:
    track = tracks[current_index]
    video_id = track.get("videoId")
    if not video_id:
        current_index += 1
        continue

    url = f"https://www.youtube.com/watch?v={video_id}"

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        stream_url = info.get("url")

    title = track.get("title", "Unknown Title")
    print(f"Playing: {title}")

    # Set up VLC media and play
    media = instance.media_new(stream_url)
    player.set_media(media)
    player.play()

    # Reset skip flags for this track
    skip_next = False
    skip_prev = False

    # Wait for the track to finish or until a skip command is issued.
    # If duration is available, we also use it to avoid looping forever.
    duration = info.get("duration", 0)
    start_time = time.time()

    while player.is_playing():
        if quit_flag or skip_next or skip_prev:
            player.stop()
            break
        # If we have a duration, break after a bit longer than that.
        if duration and (time.time() - start_time) > (duration + 2):
            break
        time.sleep(1)

    # Decide next track based on flags
    if quit_flag:
        break
    elif skip_next:
        current_index += 1
    elif skip_prev:
        current_index = max(0, current_index - 1)
    else:
        # Finished naturally, move to next
        current_index += 1

print("Finished playing or quitting the playlist!")
