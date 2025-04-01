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
    python3 chat_from_txt.py TEXTFILE [POSITION]

Arguments:
    TEXTFILE    Path to the tab-separated text file containing video information (required)
    POSITION    Position of the video in text file to process (optional)
                If not provided, processes all videos in the file
"""

import sys
import os
import subprocess
import re
import shutil

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

def run_live_chat_script(video_id):
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
    
    # Check if the JSON file already exists in any location
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
        
        # Run the live_chat.py script with the video ID
        cmd = ["python3", "live_chat.py", video_id, "-o", "json"]
        print(f"Running: {' '.join(cmd)}")
        
        # Execute the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # The live_chat.py script outputs to <videoId>_live_chat_replay.json
        src_file = os.path.join("json", live_chat_output)
        dst_file = os.path.join("json", expected_output)
        
        # Check if the output file was created
        if os.path.exists(src_file):
            # Rename to our expected format for consistency
            print(f"Renaming {src_file} to {dst_file} for consistency...")
            shutil.copy2(src_file, dst_file)
            return dst_file
                
        print(f"Warning: Expected output file not found after running live_chat.py")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running live_chat.py: {e}")
        print(f"Script output: {e.stdout}")
        print(f"Script error: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def process_video(video):
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
            
            return True
    
    # Run the live_chat.py script
    output_file = run_live_chat_script(video_id)
    if not output_file:
        print(f"Failed to get chat data for video: {title}")
        return False
    
    print(f"Successfully downloaded chat data: {output_file}")
    return True

def main():
    """Main function."""
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Error: Text file path is required")
        print(__doc__)
        sys.exit(1)
    
    text_path = sys.argv[1]
    target_position = None
    
    # If position is provided, parse it
    if len(sys.argv) >= 3:
        try:
            target_position = int(sys.argv[2])
        except ValueError:
            print(f"Error: Position must be a number, got: {sys.argv[2]}")
            sys.exit(1)
    
    # Read the text file
    videos = read_text_file(text_path)
    
    if not videos:
        print("No videos found in the text file.")
        sys.exit(1)
    
    print(f"Found {len(videos)} videos in {text_path}")
    
    # Process specific video or all videos
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
            process_video(target_video)
        else:
            print(f"Error: No video found at position {target_position}")
    else:
        # Process all videos
        successful_count = 0
        for video in videos:
            success = process_video(video)
            if success:
                successful_count += 1
        
        print(f"\nProcessed {successful_count} out of {len(videos)} videos successfully")

if __name__ == "__main__":
    main()