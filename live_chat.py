#!/usr/bin/env python3
"""
YouTube Live Chat Replay Downloader
-----------------------------------
This script downloads the live chat replay from YouTube videos by extracting
the live chat JSON data directly from the video metadata.
"""

import argparse
import json
import os
import re
import requests
import sys
import time
from urllib.parse import parse_qs, urlparse

USER_AGENTS = {
    "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
}

def get_video_info(video_id, user_agent):
    """Get video metadata from YouTube."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: Could not fetch video page. Status code: {response.status_code}")
        sys.exit(1)
    
    html_content = response.text
    
    # Try to extract ytInitialData
    data_match = re.search(r'var ytInitialData\s*=\s*(\{.+?\});', html_content)
    if not data_match:
        data_match = re.search(r'window\["ytInitialData"\]\s*=\s*(\{.+?\});', html_content)
    
    if not data_match:
        print("Error: Could not find ytInitialData in the video page.")
        sys.exit(1)
    
    try:
        yt_data = json.loads(data_match.group(1))
    except json.JSONDecodeError:
        print("Error: Could not parse ytInitialData as JSON.")
        sys.exit(1)
    
    # Try to extract player response
    player_match = re.search(r'var ytInitialPlayerResponse\s*=\s*(\{.+?\});', html_content)
    if not player_match:
        player_match = re.search(r'window\["ytInitialPlayerResponse"\]\s*=\s*(\{.+?\});', html_content)
    
    if not player_match:
        print("Error: Could not find ytInitialPlayerResponse in the video page.")
        sys.exit(1)
    
    try:
        player_data = json.loads(player_match.group(1))
    except json.JSONDecodeError:
        print("Error: Could not parse ytInitialPlayerResponse as JSON.")
        sys.exit(1)
        
    return yt_data, player_data

def extract_chat_replay_url(player_data):
    """Extract live chat replay URL from player data."""
    try:
        # Check if live chat replay exists in the subtitles section
        if "captions" in player_data and "playerCaptionsTracklistRenderer" in player_data["captions"]:
            captions = player_data["captions"]["playerCaptionsTracklistRenderer"]
            if "captionTracks" in captions:
                for track in captions["captionTracks"]:
                    if track.get("kind") == "asr" or "live_chat" in track.get("name", {}).get("simpleText", "").lower():
                        return track["baseUrl"]
        
        # Alternative method: Look for liveChatRenderer in ytInitialData
        if "liveChatRenderer" in json.dumps(player_data):
            # The presence indicates there's a live chat, but we need continuation tokens
            video_id = player_data.get("videoDetails", {}).get("videoId")
            if video_id:
                return f"https://www.youtube.com/live_chat_replay?v={video_id}"
    except Exception as e:
        print(f"Error extracting chat replay URL: {e}")
    
    return None

def get_continuation_tokens(yt_data):
    """Extract continuation tokens for live chat replay."""
    try:
        # Search for liveChatRenderer and extract continuation token
        json_str = json.dumps(yt_data)
        continuation_match = re.search(r'"continuation":"([^"]+)"', json_str)
        if continuation_match:
            return continuation_match.group(1)
        
        # Alternative locations for the continuation token
        contents = yt_data.get("contents", {}).get("twoColumnWatchNextResults", {}).get("conversationBar", {}).get("liveChatRenderer", {})
        if contents:
            actions = contents.get("actions", [])
            for action in actions:
                if "replayChatItemAction" in action:
                    return action["replayChatItemAction"].get("continuation", {}).get("replayContinuationData", {}).get("continuation")
    except Exception as e:
        print(f"Error extracting continuation tokens: {e}")
    
    return None

def fetch_chat_replay(video_id, user_agent, output_dir="."):
    """Fetch and save the live chat replay."""
    print(f"Fetching live chat replay for video ID: {video_id}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get video information
    yt_data, player_data = get_video_info(video_id, user_agent)
    
    # Extract chat replay URL
    chat_url = extract_chat_replay_url(player_data)
    if not chat_url:
        # Try to get continuation token
        continuation = get_continuation_tokens(yt_data)
        if continuation:
            chat_url = f"https://www.youtube.com/live_chat_replay/get_live_chat_replay?continuation={continuation}"
        else:
            print("Error: Could not find live chat replay data in the video.")
            print("This video might not have a live chat replay available.")
            sys.exit(1)
    
    print(f"Found live chat replay URL: {chat_url}")
    
    # Create headers for chat request
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.youtube.com/watch?v={video_id}"
    }
    
    # Fetch the live chat data
    print("Downloading live chat replay data...")
    response = requests.get(chat_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Failed to download live chat replay. Status code: {response.status_code}")
        sys.exit(1)
    
    # Determine appropriate filename
    output_file = os.path.join(output_dir, f"{video_id}_live_chat_replay.json")
    
    # Save the raw chat data
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # Try to parse as JSON first
            try:
                chat_data = response.json()
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                # If not valid JSON, save as raw text
                f.write(response.text)
        
        print(f"Successfully saved live chat replay to: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error saving chat replay: {e}")
        sys.exit(1)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Download YouTube live chat replays")
    parser.add_argument("video_id", help="YouTube video ID or URL")
    parser.add_argument("-b", "--browser", choices=["chrome", "firefox", "edge", "safari"], 
                        default="chrome", help="Browser to emulate (default: chrome)")
    parser.add_argument("-o", "--output-dir", default=".", 
                        help="Output directory for the chat replay file (default: current directory)")
    
    args = parser.parse_args()
    
    # Check if input is a full URL and extract video ID if needed
    if "youtube.com" in args.video_id or "youtu.be" in args.video_id:
        parsed_url = urlparse(args.video_id)
        if parsed_url.netloc == "youtu.be":
            video_id = parsed_url.path.lstrip("/")
        else:
            query_params = parse_qs(parsed_url.query)
            video_id = query_params.get("v", [""])[0]
        
        if not video_id:
            print("Error: Could not extract video ID from URL.")
            sys.exit(1)
        
        args.video_id = video_id
    
    return args

def main():
    """Main function."""
    args = parse_args()
    
    # Get user agent for the selected browser
    user_agent = USER_AGENTS.get(args.browser)
    
    # Fetch and save the live chat replay
    output_file = fetch_chat_replay(args.video_id, user_agent, args.output_dir)
    
    print("\nDone! Live chat replay has been downloaded.")
    print(f"File saved to: {output_file}")

if __name__ == "__main__":
    main()