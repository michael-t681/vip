#!/usr/bin/env python3
"""
YouTube Chat Downloader for Videos in Text File

This script reads a tab-separated text file containing YouTube video information
and runs a chat.py script to download the live chat replay for specific videos.
The output stays in JSON format with the filename: <videoId>_live_chat.json

The script checks if files already exist in both the current directory and a 'json'
subdirectory before downloading, allowing for resuming interrupted processes
without duplicating work.

Usage:
    python3 chat_from_txt.py TEXTFILE [POSITION]

Arguments:
    TEXTFILE    Path to the tab-separated text file containing video information (required)
    POSITION    Position of the video in text file to process (optional, defaults to 1)
                If not provided, processes all videos in the file
"""

import sys
import os
import subprocess
import re

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

def run_chat_script(video_id):
    """Run the chat.py script to download chat data for a specific video."""
    # Define possible locations for the JSON file
    expected_output = f"{video_id}_live_chat.json"
    possible_locations = [
        expected_output,                           # Current directory
        os.path.join("json", expected_output)      # json subdirectory
    ]
    
    # Check if the JSON file already exists in any location
    for file_path in possible_locations:
        if os.path.exists(file_path):
            print(f"Chat data already exists at {file_path}. Skipping download.")
            return file_path
    
    try:
        # Run the chat.py script with the video ID
        cmd = ["python3", "chat.py", video_id]
        print(f"Running: {' '.join(cmd)}")
        
        # Execute the command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Check again for the output file in possible locations
        for file_path in possible_locations:
            if os.path.exists(file_path):
                return file_path
                
        print(f"Warning: Expected output file {expected_output} not found after running chat.py")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running chat.py: {e}")
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
    possible_locations = [
        json_filename,                       # Current directory
        os.path.join("json", json_filename)  # json subdirectory
    ]
    
    # Check if output file already exists in any location
    for file_path in possible_locations:
        if os.path.exists(file_path):
            print(f"Chat data file already exists at {file_path}. Skipping download.")
            return True
    
    # Run the chat.py script
    output_file = run_chat_script(video_id)
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