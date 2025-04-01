#!/usr/bin/env python3
"""
YouTube Chat Downloader for Videos in Text File

This script reads a tab-separated text file containing YouTube video information
and runs live_chat.py to download the live chat replay for specific videos.
The output is saved in JSON format with the filename: <videoId>_live_chat.json

The script checks if files already exist in both the current directory and a 'json'
subdirectory before downloading, allowing for resuming interrupted processes
without duplicating work.

Usage:
    python3 chat_from_txt.py TEXTFILE [OPTIONS]

Arguments:
    TEXTFILE    Path to the tab-separated text file containing video information (required)

Options:
    --position POSITION     Position of a specific video to process
    --start POSITION        Starting position to begin processing videos from
    --force                 Force redownload even if the file already exists
    --timeout SECONDS       Set timeout in seconds for download operations (default: 300)
"""

import sys
import os
import subprocess
import re
import shutil
import argparse
import time
import signal

# Global variable to track if we're being interrupted
interrupted = False

def signal_handler(sig, frame):
    """Handle interrupt signals gracefully."""
    global interrupted
    print("\nInterrupt received, finishing current download and exiting...")
    interrupted = True

# Register the signal handler for CTRL+C
signal.signal(signal.SIGINT, signal_handler)

def read_text_file(text_path):
    """Read video information from a tab-separated text file."""
    videos = []
    try:
        with open(text_path, 'r', encoding='utf-8') as file:
            # Read all lines
            lines = file.readlines()
            
            # Skip empty lines
            lines = [line for line in lines if line.strip()]
            
            if not lines:
                print(f"Error: Text file is empty: {text_path}")
                sys.exit(1)
            
            # Extract headers from the first line
            headers = lines[0].strip().split('\t')
            
            # Ensure required headers exist
            if 'Position' not in headers or 'Video ID' not in headers or 'Title' not in headers:
                print(f"Error: Text file must contain columns: Position, Video ID, Title")
                sys.exit(1)
            
            # Map headers to column indices
            headers_map = {header: idx for idx, header in enumerate(headers)}
            position_idx = headers_map.get('Position')
            video_id_idx = headers_map.get('Video ID')
            title_idx = headers_map.get('Title')
            
            # Process data rows
            for line in lines[1:]:  # Skip header row
                columns = line.strip().split('\t')
                
                # Skip rows with insufficient columns
                if len(columns) <= max(position_idx, video_id_idx, title_idx):
                    print(f"Warning: Skipping row with insufficient columns: {line.strip()}")
                    continue
                
                video = {
                    "position": columns[position_idx],
                    "videoId": columns[video_id_idx],
                    "title": columns[title_idx]
                }
                videos.append(video)
        
        return videos
    except FileNotFoundError:
        print(f"Error: Text file not found: {text_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading text file: {e}")
        sys.exit(1)

def run_live_chat_script(video_id, timeout=300, force=False):
    """Run the live_chat.py script to download chat data for a specific video."""
    # Define expected output filenames
    expected_output = f"{video_id}_live_chat.json"
    live_chat_output = f"{video_id}_live_chat_replay.json"
    
    possible_locations = [
        expected_output,                           # Standard output name
        live_chat_output,                          # Output name from live_chat.py
        os.path.join("json", expected_output),     # json subdirectory with standard name
        os.path.join("json", live_chat_output)     # json subdirectory with live_chat.py name
    ]
    
    # Check if the JSON file already exists in any location (unless force is True)
    if not force:
        for file_path in possible_locations:
            if os.path.exists(file_path):
                print(f"Chat data already exists at {file_path}.")
                
                # If it's already in the expected format, just return it
                if file_path == expected_output or file_path == os.path.join("json", expected_output):
                    return file_path
                
                # Otherwise, we'll need to rename it to the expected format
                target_path = expected_output if os.path.dirname(file_path) == "" else os.path.join("json", expected_output)
                print(f"Renaming {file_path} to {target_path} for consistency...")
                shutil.copy2(file_path, target_path)
                return target_path
    
    try:
        # Create json directory if it doesn't exist
        if not os.path.exists("json"):
            os.makedirs("json")
        
        # Handle video IDs that start with a hyphen by using -- to mark end of options
        if video_id.startswith('-'):
            cmd = ["python3", "live_chat.py", "--", video_id, "-o", "json"]
        else:
            cmd = ["python3", "live_chat.py", video_id, "-o", "json"]
            
        print(f"Running: {' '.join(cmd)}")
        
        # Execute the command with timeout
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
            
            # The live_chat.py script outputs to <videoId>_live_chat_replay.json
            src_file = os.path.join("json", live_chat_output)
            dst_file = os.path.join("json", expected_output)
            
            # Check if the output file was created
            if os.path.exists(src_file):
                # Rename to our expected format for consistency
                print(f"Renaming {src_file} to {dst_file} for consistency...")
                shutil.copy2(src_file, dst_file)
                return dst_file
            
            # Check if output was created with the expected_output name directly
            if os.path.exists(os.path.join("json", expected_output)):
                return os.path.join("json", expected_output)
                    
            print(f"Warning: Expected output file not found after running live_chat.py")
            return None
        except subprocess.TimeoutExpired:
            print(f"Error: Command timed out after {timeout} seconds")
            return None
            
    except subprocess.CalledProcessError as e:
        # Check for common error patterns
        if "Error: Could not find live chat replay data in the video" in e.stdout:
            print(f"No live chat data available for this video (video might not have had a live chat)")
        else:
            print(f"Error running live_chat.py: {e}")
            print(f"Script output: {e.stdout}")
            print(f"Script error: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def process_video(video, timeout=300, force=False):
    """Process a single video: download chat data."""
    video_id = video["videoId"]
    title = video["title"]
    position = video["position"]
    
    print(f"\nProcessing video {position}: {title} (ID: {video_id})")
    
    # Expected JSON filename
    json_filename = f"{video_id}_live_chat.json"
    live_chat_filename = f"{video_id}_live_chat_replay.json"
    
    possible_locations = [
        json_filename,                           # Standard output name
        live_chat_filename,                      # Output name from live_chat.py
        os.path.join("json", json_filename),     # json subdirectory with standard name
        os.path.join("json", live_chat_filename) # json subdirectory with live_chat.py name
    ]
    
    # Check if output file already exists in any location
    file_exists = False
    if not force:
        for file_path in possible_locations:
            if os.path.exists(file_path):
                print(f"Chat data file already exists at {file_path}.")
                
                # If it's not in the expected format, rename it
                expected_path = os.path.join("json", json_filename)
                if file_path != expected_path:
                    print(f"Copying to {expected_path} for consistency...")
                    # Ensure json directory exists
                    if not os.path.exists("json"):
                        os.makedirs("json")
                    shutil.copy2(file_path, expected_path)
                
                file_exists = True
                break
    
    if file_exists and not force:
        return True
    
    # Run the live_chat.py script
    output_file = run_live_chat_script(video_id, timeout, force)
    if not output_file:
        print(f"Failed to get chat data for video: {title}")
        return False
    
    print(f"Successfully downloaded chat data: {output_file}")
    return True

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Download YouTube chat data for videos in a text file")
    parser.add_argument("text_file", help="Path to the tab-separated text file containing video information")
    parser.add_argument("--position", type=int, help="Position of a specific video to process")
    parser.add_argument("--start", type=int, help="Starting position to begin processing videos from")
    parser.add_argument("--force", action="store_true", help="Force redownload even if files exist")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds for download operations (default: 300)")
    return parser.parse_args()

def main():
    """Main function."""
    # Parse command line arguments
    args = parse_args()
    
    text_path = args.text_file
    target_position = args.position
    start_position = args.start
    force = args.force
    timeout = args.timeout
    
    # Read the text file
    videos = read_text_file(text_path)
    
    if not videos:
        print("No videos found in the text file.")
        sys.exit(1)
    
    print(f"Found {len(videos)} videos in {text_path}")
    
    # Process specific video or all videos from a starting position
    if target_position is not None:
        # Find the video with the specified position
        target_video = None
        for video in videos:
            # Convert position to integer for comparison
            try:
                video_position = int(video["position"])
                if video_position == target_position:
                    target_video = video
                    break
            except ValueError:
                # Skip videos with non-integer positions
                continue
        
        if target_video:
            process_video(target_video, timeout, force)
        else:
            print(f"Error: No video found at position {target_position}")
    else:
        # Process all videos, starting from the specified position if provided
        videos_to_process = videos
        
        if start_position is not None:
            # Filter videos to only include those with position >= start_position
            videos_to_process = []
            for video in videos:
                try:
                    video_position = int(video["position"])
                    if video_position >= start_position:
                        videos_to_process.append(video)
                except ValueError:
                    # Skip videos with non-integer positions
                    continue
            
            print(f"Starting from position {start_position}. {len(videos_to_process)} videos will be processed.")
        
        successful_count = 0
        for video in videos_to_process:
            # Check if user interrupted the process
            if interrupted:
                print("Interrupted by user. Stopping processing.")
                break
                
            success = process_video(video, timeout, force)
            if success:
                successful_count += 1
            
            # Add a small delay between requests to avoid overloading
            if not interrupted:
                time.sleep(1)
        
        print(f"\nProcessed {successful_count} out of {len(videos_to_process)} videos successfully")

if __name__ == "__main__":
    main()