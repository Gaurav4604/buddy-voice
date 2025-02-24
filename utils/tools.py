import os
import time
from ytmusicapi import YTMusic, OAuthCredentials
from yt_dlp import YoutubeDL
import vlc

# Ensure VLC’s DLLs can be found (adjust this path to your installation)
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")

# Set up ytmusicapi (ensure your oauth.json is properly configured)
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
ytmusic = YTMusic(
    "oauth.json",
    oauth_credentials=OAuthCredentials(
        client_id=client_id, client_secret=client_secret
    ),
)

# Options for yt-dlp to extract the best audio stream without downloading
ydl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "skip_download": True,
}

# Initialize VLC instance and media player
vlc_instance = vlc.Instance()
player = vlc_instance.media_player_new()


def play_search(query: str) -> None:
    """
    Search for a song matching 'query', and play the first result.
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

    # Optionally, wait until playback is finished
    while player.is_playing():
        time.sleep(1)
