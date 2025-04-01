#!/usr/bin/env python3
"""
YouTube Playlist Extractor using yt-dlp

This script extracts metadata from YouTube playlists including video IDs, titles,
publication dates, view counts, and comment counts using yt-dlp.

Usage:
    python youtube_playlist_extractor_ytdlp.py PLAYLIST_ID [--output OUTPUT_FILE]

Arguments:
    PLAYLIST_ID      YouTube playlist ID or full URL
    --output         Output file name (default: playlist_videos.txt)

Requirements:
    yt-dlp: pip install yt-dlp
"""

import os
import sys
import re
import json
import argparse
import datetime
import subprocess
from urllib.parse import urlparse, parse_qs

def extract_playlist_id(url_or_id):
    """Extract playlist ID from a URL or return the ID if already provided."""
    if not url_or_id.startswith('http'):
        return url_or_id
    
    parsed_url = urlparse(url_or_id)
    
    # Handle youtube.com URLs
    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        if 'list' in query_params:
            return query_params['list'][0]
    
    # Handle youtu.be URLs
    elif 'youtu.be' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        if 'list' in query_params:
            return query_params['list'][0]
    
    print(f"Error: Could not extract playlist ID from URL: {url_or_id}")
    sys.exit(1)

def format_view_count(view_count):
    """Format view count with commas."""
    try:
        return f"{int(view_count):,}"
    except (ValueError, TypeError):
        return view_count or "N/A"

def format_duration(duration_seconds):
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if not duration_seconds:
        return "N/A"
    
    try:
        seconds = int(float(duration_seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return str(duration_seconds)

def format_date(timestamp):
    """Format Unix timestamp to YYYY-MM-DD."""
    if not timestamp:
        return "N/A"
    
    try:
        dt = datetime.datetime.fromtimestamp(int(timestamp))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(timestamp)

def check_yt_dlp_installed():
    """Check if yt-dlp is installed."""
    try:
        subprocess.run(["yt-dlp", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def get_playlist_videos_with_ytdlp(playlist_id):
    """Get playlist videos using yt-dlp."""
    videos = []
    
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"Fetching playlist data for: {playlist_url}")
    
    # Set up yt-dlp command
    cmd = [
        "yt-dlp",
        "--flat-playlist",  # Don't download videos
        "--no-warnings",    # Reduce output noise
        "--dump-json",      # Output video info as JSON
        "--playlist-items", "1-1000",  # Limit to first 1000 items for safety
        playlist_url
    ]
    
    try:
        # Run yt-dlp and capture output
        process = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Process each line of output
        for i, line in enumerate(process.stdout.splitlines()):
            if not line.strip():
                continue
            
            try:
                video_data = json.loads(line)
                
                videos.append({
                    "position": i + 1,
                    "videoId": video_data.get("id", "N/A"),
                    "title": video_data.get("title", "N/A"),
                    "publishedAt": format_date(video_data.get("timestamp")),
                    "channelTitle": video_data.get("channel", "N/A"),
                    "viewCount": format_view_count(video_data.get("view_count")),
                    "commentCount": format_view_count(video_data.get("comment_count")),
                    "duration": format_duration(video_data.get("duration")),
                    "channel_id": video_data.get("channel_id", "N/A")
                })
                
                # Print progress
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1} videos...")
            
            except json.JSONDecodeError:
                print(f"Warning: Could not parse JSON for video at position {i + 1}")
    
    except subprocess.CalledProcessError as e:
        print(f"Error running yt-dlp: {e}")
        print(f"Error output: {e.stderr}")
        
        # If we're getting a restricted playlist, try with more details
        if "The playlist does not exist" in e.stderr or "Private video" in e.stderr or "Sign in to confirm your age" in e.stderr:
            print("Trying to fetch with additional details...")
            return get_playlist_videos_with_ytdlp_detailed(playlist_id)
    
    print(f"Total videos found: {len(videos)}")
    return videos

def get_playlist_videos_with_ytdlp_detailed(playlist_id):
    """Get more detailed playlist videos using yt-dlp."""
    videos = []
    
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"Fetching detailed playlist data for: {playlist_url}")
    
    # Set up yt-dlp command with more details
    cmd = [
        "yt-dlp",
        "--skip-download",       # Don't download videos
        "--no-warnings",         # Reduce output noise
        "--dump-json",           # Output video info as JSON
        "--playlist-items", "1-1000",  # Limit to first 1000 items for safety
        "--write-info-json",     # Write video info to JSON files
        "--no-write-playlist-metafiles",  # Don't write playlist metadata files
        playlist_url
    ]
    
    try:
        # Create a temporary directory for JSON files
        temp_dir = "temp_ytdlp_json"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Set current directory to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        
        # Run yt-dlp and capture output
        process = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Process each line of output
        for i, line in enumerate(process.stdout.splitlines()):
            if not line.strip():
                continue
            
            try:
                video_data = json.loads(line)
                
                videos.append({
                    "position": i + 1,
                    "videoId": video_data.get("id", "N/A"),
                    "title": video_data.get("title", "N/A"),
                    "publishedAt": format_date(video_data.get("timestamp")),
                    "channelTitle": video_data.get("channel", "N/A"),
                    "viewCount": format_view_count(video_data.get("view_count")),
                    "commentCount": format_view_count(video_data.get("comment_count")),
                    "duration": format_duration(video_data.get("duration")),
                    "channel_id": video_data.get("channel_id", "N/A")
                })
                
                # Print progress
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1} videos...")
            
            except json.JSONDecodeError:
                print(f"Warning: Could not parse JSON for video at position {i + 1}")
        
        # Return to original directory
        os.chdir(original_dir)
        
    except subprocess.CalledProcessError as e:
        print(f"Error running yt-dlp in detailed mode: {e}")
        print(f"Error output: {e.stderr}")
        
        # Return to original directory in case of error
        if os.getcwd() != original_dir:
            os.chdir(original_dir)
    
    print(f"Total videos found with detailed mode: {len(videos)}")
    return videos

def save_videos_to_file(videos, output_file):
    """Save video details to a tab-separated text file."""
    print(f"Saving {len(videos)} videos to {output_file}")
    
    # Create directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_file, "w", encoding="utf-8") as f:
        # Write header
        f.write("Position\tVideo ID\tTitle\tPublished Date\tChannel\tViews\tComments\tDuration\tChannel ID\n")
        
        # Write video details
        for video in videos:
            f.write(f"{video['position']}\t")
            f.write(f"{video['videoId']}\t")
            f.write(f"{video['title']}\t")
            f.write(f"{video.get('publishedAt', 'N/A')}\t")
            f.write(f"{video.get('channelTitle', 'N/A')}\t")
            f.write(f"{video.get('viewCount', 'N/A')}\t")
            f.write(f"{video.get('commentCount', 'N/A')}\t")
            f.write(f"{video.get('duration', 'N/A')}\t")
            f.write(f"{video.get('channel_id', 'N/A')}\n")
    
    print(f"Videos successfully saved to {output_file}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Extract video IDs and metadata from a YouTube playlist using yt-dlp")
    parser.add_argument("playlist_id", help="YouTube playlist ID or URL")
    parser.add_argument("--output", default="playlist_videos.txt", help="Output file name")
    
    return parser.parse_args()

def main():
    """Main function."""
    # Check if yt-dlp is installed
    if not check_yt_dlp_installed():
        print("Error: yt-dlp is not installed or not found in PATH.")
        print("Please install it with: pip install yt-dlp")
        sys.exit(1)
    
    args = parse_args()
    
    # Extract playlist ID if a URL was provided
    playlist_id = extract_playlist_id(args.playlist_id)
    print(f"Using playlist ID: {playlist_id}")
    
    # Get videos from the playlist
    videos = get_playlist_videos_with_ytdlp(playlist_id)
    
    # Save videos to a file
    if videos:
        save_videos_to_file(videos, args.output)
        print(f"Extraction complete. Found {len(videos)} videos.")
    else:
        print("No videos were extracted from the playlist.")

if __name__ == "__main__":
    main()