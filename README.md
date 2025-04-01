# Usage

python3 -m venv .venv

source /venv/bin/activate

python3 ytpedlp.py PLRcT6n7GfrWMPlNxiAHizLIKLm4H2fTZW
- downloads list of streams to playlist_videos.txt

mkdir json

python3 chat_from_txt.py playlist_videos.txt
- downloads chat data to json/<videoId>_live_chat.json
- can do singular video or start from a position



