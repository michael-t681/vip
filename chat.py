#!/usr/bin/env python3
"""
YouTube Live Chat Replay Downloader using pytchat (Fixed Version)
----------------------------------------------------------------
This script downloads the live chat replay from a YouTube video using
the pytchat library, with improved error handling.

Prerequisites:
- pytchat library: pip install pytchat
- pandas (optional, for analysis): pip install pandas
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime, timedelta
import pandas as pd

def download_live_chat_replay(video_id, output_dir="."):
    """Download live chat replay using pytchat."""
    print(f"Downloading live chat replay for video ID: {video_id}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # Import pytchat here to handle import errors better
        import pytchat
        
        # Initialize pytchat for chat replay
        chat = pytchat.create(video_id=video_id)
        
        if not chat:
            print(f"Failed to initialize chat for video {video_id}")
            return None
        
        # Check if chat is available
        if not chat.is_alive():
            print(f"No live chat replay available for video {video_id}")
            return None
        
        # Prepare to collect messages
        all_messages = []
        message_count = 0
        start_time = time.time()
        
        print("Starting chat replay download...")
        
        # Get all chat messages
        while chat.is_alive():
            # Get new data
            data = chat.get()
            items = data.items
            
            if items:
                # Process each chat item
                for item in items:
                    try:
                        # Create a simpler, safer dictionary with error handling
                        message_data = {
                            "author_name": getattr(item.author, 'name', ''),
                            "author_id": getattr(item.author, 'channelId', ''),
                            "message": getattr(item, 'message', ''),
                            "timestamp": getattr(item, 'timestamp', 0),
                            "datetime": str(getattr(item, 'datetime', '')),
                            "time_in_seconds": getattr(item, 'elapsedTime', 0),
                            "is_member": getattr(item.author, 'isChatSponsor', False),
                            "is_moderator": getattr(item.author, 'isChatModerator', False),
                            "is_owner": getattr(item.author, 'isChatOwner', False)
                        }
                        
                        # Add superchat information if available
                        if hasattr(item, 'amountValue') and item.amountValue:
                            message_data["is_superchat"] = True
                            message_data["amount"] = item.amountValue
                            message_data["amount_string"] = getattr(item, 'amountString', '')
                            message_data["currency"] = getattr(item, 'currency', '')
                        else:
                            message_data["is_superchat"] = False
                        
                        all_messages.append(message_data)
                    except Exception as e:
                        print(f"Error processing chat item: {e}")
                        continue
                
                # Update count
                message_count = len(all_messages)
                
                # Print progress
                elapsed = time.time() - start_time
                print(f"\rDownloaded {message_count} messages... ({elapsed:.1f} seconds)", end="")
                
                # Save intermediate results every 1000 messages
                if message_count % 1000 == 0:
                    intermediate_file = os.path.join(output_dir, f"{video_id}_chat_temp.json")
                    with open(intermediate_file, "w", encoding="utf-8") as f:
                        json.dump(all_messages, f, ensure_ascii=False, indent=2)
            
            # Pause briefly to avoid high CPU usage
            time.sleep(0.1)
        
        print("\nChat replay download complete.")
    
    except ImportError:
        print("\nError: The pytchat library is not installed.")
        print("Please install it with: pip install pytchat")
        return None
    except Exception as e:
        print(f"\nError during download: {e}")
        if all_messages:
            print(f"Saving {len(all_messages)} messages collected before the error...")
        else:
            return None
    
    # Save all messages
    if all_messages:
        output_file = os.path.join(output_dir, f"{video_id}_live_chat.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_messages, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved {len(all_messages)} chat messages to: {output_file}")
        return output_file
    else:
        print("No chat messages were found for this video.")
        return None

def format_time_from_seconds(seconds):
    """Convert seconds to HH:MM:SS format."""
    return str(timedelta(seconds=seconds))

def analyze_chat_data(file_path):
    """Analyze the downloaded chat data and provide insights."""
    print("\nAnalyzing chat data...")
    
    try:
        # Load the data
        with open(file_path, "r", encoding="utf-8") as f:
            chat_data = json.load(f)
        
        # Convert to DataFrame
        df = pd.DataFrame(chat_data)
        
        # Basic statistics
        total_messages = len(df)
        unique_authors = df["author_name"].nunique()
        
        # Author statistics
        top_authors = df["author_name"].value_counts().head(10)
        
        # Super chat statistics
        if "is_superchat" in df.columns:
            superchat_count = df["is_superchat"].sum()
            superchat_amount = 0
            if superchat_count > 0 and "amount" in df.columns:
                superchat_amount = df[df["is_superchat"]]["amount"].sum()
        
        # Time statistics
        if "time_in_seconds" in df.columns:
            df["minute_mark"] = (df["time_in_seconds"] // 60).astype(int)
            messages_per_minute = df.groupby("minute_mark").size()
            peak_minute = messages_per_minute.idxmax()
            peak_count = messages_per_minute.max()
            
            # Get 5-minute intervals
            df["five_min_interval"] = (df["time_in_seconds"] // 300).astype(int) * 5
            messages_per_5min = df.groupby("five_min_interval").size()
            top_5min_intervals = messages_per_5min.nlargest(5)
            
            # Get 10-minute intervals
            df["ten_min_interval"] = (df["time_in_seconds"] // 600).astype(int) * 10
            messages_per_10min = df.groupby("ten_min_interval").size()
            top_10min_intervals = messages_per_10min.nlargest(5)
        
        # Print summary
        print("\n" + "="*50)
        print("CHAT ANALYSIS SUMMARY")
        print("="*50)
        
        print(f"\nTotal Messages: {total_messages}")
        print(f"Unique Authors: {unique_authors}")
        
        if "is_superchat" in df.columns:
            print(f"Super Chat Messages: {superchat_count}")
            if superchat_count > 0 and "amount" in df.columns:
                print(f"Super Chat Total: {superchat_amount:.2f}")
        
        print("\nTop 10 Commenters:")
        for author, count in top_authors.items():
            print(f"  - {author}: {count} messages")
        
        if "time_in_seconds" in df.columns:
            print(f"\nPeak Minute: Minute {peak_minute} with {peak_count} messages")
            print(f"Peak Time: {format_time_from_seconds(peak_minute * 60)}")
            
            print("\n5-Minute Intervals with Most Activity:")
            for interval, count in top_5min_intervals.items():
                start_time = format_time_from_seconds(interval * 60)
                end_time = format_time_from_seconds((interval + 5) * 60)
                print(f"  - {start_time} to {end_time}: {count} messages")
            
            print("\n10-Minute Intervals with Most Activity:")
            for interval, count in top_10min_intervals.items():
                start_time = format_time_from_seconds(interval * 60)
                end_time = format_time_from_seconds((interval + 10) * 60)
                print(f"  - {start_time} to {end_time}: {count} messages")
        
        print("\n" + "="*50)
        
        # Save analysis as CSV files
        analysis_dir = os.path.join(os.path.dirname(file_path), "analysis")
        if not os.path.exists(analysis_dir):
            os.makedirs(analysis_dir)
        
        # Save top authors
        top_authors_df = top_authors.reset_index()
        top_authors_df.columns = ["author", "message_count"]
        top_authors_df.to_csv(os.path.join(analysis_dir, "top_authors.csv"), index=False)
        
        if "time_in_seconds" in df.columns:
            # Save minute activity
            minute_activity = messages_per_minute.reset_index()
            minute_activity.columns = ["minute", "message_count"]
            minute_activity.to_csv(os.path.join(analysis_dir, "minute_activity.csv"), index=False)
            
            # Save 5-minute intervals
            five_min_activity = messages_per_5min.reset_index()
            five_min_activity.columns = ["five_min_interval", "message_count"]
            five_min_activity.to_csv(os.path.join(analysis_dir, "five_min_activity.csv"), index=False)
            
            # Save 10-minute intervals
            ten_min_activity = messages_per_10min.reset_index()
            ten_min_activity.columns = ["ten_min_interval", "message_count"]
            ten_min_activity.to_csv(os.path.join(analysis_dir, "ten_min_activity.csv"), index=False)
        
        print(f"Analysis files saved to {analysis_dir}")
        
    except ImportError:
        print("Pandas is required for analysis. Please install with 'pip install pandas'")
    except Exception as e:
        print(f"Error analyzing chat data: {e}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="YouTube Live Chat Replay Downloader")
    parser.add_argument("video_id", help="YouTube video ID or URL")
    parser.add_argument("-o", "--output-dir", default=".", 
                        help="Output directory for the chat replay file (default: current directory)")
    parser.add_argument("--no-analysis", action="store_true",
                        help="Skip chat data analysis")
    
    args = parser.parse_args()
    
    # Extract video ID from URL if needed
    if "youtube.com" in args.video_id or "youtu.be" in args.video_id:
        if "youtube.com" in args.video_id:
            # Extract v parameter from URL
            try:
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(args.video_id)
                video_id = parse_qs(parsed_url.query)['v'][0]
            except:
                print("Could not extract video ID from YouTube URL")
                sys.exit(1)
        else:  # youtu.be
            video_id = args.video_id.split("/")[-1]
        
        args.video_id = video_id
    
    return args

def main():
    """Main function."""
    args = parse_args()
    
    # Download live chat replay
    output_file = download_live_chat_replay(args.video_id, args.output_dir)
    
    # Analyze chat data if available
    if output_file and not args.no_analysis:
        try:
            analyze_chat_data(output_file)
        except Exception as e:
            print(f"Error during analysis: {e}")
    
    if output_file:
        print(f"\nChat replay has been downloaded to: {output_file}")
    else:
        print("\nFailed to download chat replay. This might happen if:")
        print("- The video doesn't have chat replay available")
        print("- The video was not a live stream")
        print("- Chat was disabled during the live stream")
        print("- The chat replay has been removed by the channel owner")

if __name__ == "__main__":
    main()