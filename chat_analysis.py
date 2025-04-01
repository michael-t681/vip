#!/usr/bin/env python3
"""
YouTube Live Chat JSON Analyzer
-----------------------------------------------
This script analyzes YouTube live chat data from JSON files and provides
analysis of the chat data, including comment counts, top comments, and
activity intervals.
"""

import argparse
import json
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from collections import Counter

def load_chat_data(file_path):
    """Load chat data from a JSON file and return as a pandas DataFrame."""
    print(f"Loading chat data from: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        
        # Create DataFrame from the JSON data
        df = pd.DataFrame(chat_data)
        
        # Convert timestamp to datetime if it exists
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        elif 'datetime' in df.columns:
            df['timestamp'] = pd.to_datetime(df['datetime'])
        
        # Extract video_offset_seconds from time_in_seconds
        if 'time_in_seconds' in df.columns:
            # Parse time format like "2:30" or "-1:00" to seconds
            def parse_time(time_str):
                try:
                    if time_str.startswith('-'):
                        # Negative time (before stream starts)
                        time_str = time_str[1:]
                        sign = -1
                    else:
                        sign = 1
                        
                    parts = time_str.split(':')
                    if len(parts) == 2:  # MM:SS
                        return sign * (int(parts[0]) * 60 + int(parts[1]))
                    elif len(parts) == 3:  # HH:MM:SS
                        return sign * (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
                    return 0
                except:
                    return 0
                    
            df['video_offset_seconds'] = df['time_in_seconds'].apply(parse_time)
            
            # Add time markers for interval analysis
            df['minute_mark'] = (df['video_offset_seconds'] // 60).astype(int)
            df['five_minute_interval'] = (df['video_offset_seconds'] // 300).astype(int) * 5
            df['ten_minute_interval'] = (df['video_offset_seconds'] // 600).astype(int) * 10
        
        print(f"Successfully loaded {len(df)} chat messages")
        return df
    
    except Exception as e:
        print(f"Error loading chat data: {e}")
        sys.exit(1)

def analyze_chat_data(df):
    """Analyze the chat data and return summary statistics."""
    if df.empty:
        return {
            "total_comments": 0,
            "top_commenters": [],
            "top_comments": [],
            "five_minute_intervals": [],
            "ten_minute_intervals": [],
            "member_percentage": 0,
            "superchat_percentage": 0
        }
    
    # Total number of comments
    total_comments = len(df)
    
    # Top commenters (by frequency)
    author_column = 'author_name' if 'author_name' in df.columns else 'author'
    top_commenters = df[author_column].value_counts().head(10).reset_index()
    top_commenters.columns = ['author', 'comment_count']
    
    # Top comments (by length, as a simple proxy for engagement)
    df['message_length'] = df['message'].str.len()
    top_comments = df.sort_values('message_length', ascending=False).head(10)
    top_comments = top_comments[[author_column, 'message', 'time_in_seconds' if 'time_in_seconds' in df.columns else 'datetime']]
    top_comments.columns = ['author', 'message', 'timestamp_text']
    
    # Analysis by time intervals
    if 'five_minute_interval' in df.columns:
        # Five minute intervals with most comments
        five_min_intervals = df.groupby('five_minute_interval').size().reset_index()
        five_min_intervals.columns = ['five_minute_interval', 'comment_count']
        five_min_intervals = five_min_intervals.sort_values('comment_count', ascending=False).head(10)
        
        # Ten minute intervals with most comments
        ten_min_intervals = df.groupby('ten_minute_interval').size().reset_index()
        ten_min_intervals.columns = ['ten_minute_interval', 'comment_count']
        ten_min_intervals = ten_min_intervals.sort_values('comment_count', ascending=False).head(10)
        
        # Format intervals for display (convert to time format)
        def format_interval(minutes):
            hours, mins = divmod(minutes, 60)
            return f"{hours:02d}:{mins:02d}:00"
        
        five_min_intervals['time_range'] = five_min_intervals['five_minute_interval'].apply(
            lambda x: f"{format_interval(x)} - {format_interval(x+5)}"
        )
        
        ten_min_intervals['time_range'] = ten_min_intervals['ten_minute_interval'].apply(
            lambda x: f"{format_interval(x)} - {format_interval(x+10)}"
        )
    else:
        five_min_intervals = pd.DataFrame(columns=['five_minute_interval', 'comment_count', 'time_range'])
        ten_min_intervals = pd.DataFrame(columns=['ten_minute_interval', 'comment_count', 'time_range'])
    
    # Member percentage
    member_percentage = 0
    if 'is_member' in df.columns:
        member_count = df['is_member'].sum()
        member_percentage = (member_count / total_comments) * 100 if total_comments > 0 else 0
    
    # Superchat percentage
    superchat_percentage = 0
    if 'is_superchat' in df.columns:
        superchat_count = df['is_superchat'].sum()
        superchat_percentage = (superchat_count / total_comments) * 100 if total_comments > 0 else 0
    
    return {
        "total_comments": total_comments,
        "top_commenters": top_commenters,
        "top_comments": top_comments,
        "five_minute_intervals": five_min_intervals,
        "ten_minute_intervals": ten_min_intervals,
        "member_percentage": member_percentage,
        "superchat_percentage": superchat_percentage
    }

def generate_visualizations(df, file_name, output_dir):
    """Generate visualizations of the chat data."""
    if df.empty:
        print("No data available for visualization.")
        return
    
    # Extract video ID from the filename
    video_id = os.path.basename(file_name).split('_')[0]
    
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 1. Comments over time (by minute)
    if 'minute_mark' in df.columns:
        plt.figure(figsize=(12, 6))
        
        # Group by minute and count comments - NOT accumulating
        minute_counts = df.groupby('minute_mark').size()
        
        # Sort by minute mark for chronological order
        minute_counts = minute_counts.sort_index()
        
        # Convert minute marks to readable time format for x-axis
        minute_labels = [f"{m//60:02d}:{m%60:02d}" for m in minute_counts.index]
        
        # Plot the data
        plt.bar(range(len(minute_counts)), minute_counts.values, color='skyblue')
        
        # Set x-axis ticks and labels (showing fewer labels to avoid crowding)
        tick_spacing = max(1, len(minute_counts) // 20)  # Show ~20 labels at most
        plt.xticks(
            range(0, len(minute_counts), tick_spacing),
            [minute_labels[i] for i in range(0, len(minute_counts), tick_spacing)],
            rotation=45
        )
        
        plt.title('Comments per Minute')
        plt.xlabel('Stream Time (HH:MM)')
        plt.ylabel('Number of Comments')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{video_id}_comments_per_minute.png"))
        plt.close()

    # 2. Comments by 5-minute interval
    if 'five_minute_interval' in df.columns:
        plt.figure(figsize=(12, 6))
        
        # Group by 5-minute interval and count comments - NOT accumulating
        five_min_intervals = df.groupby('five_minute_interval').size()
        
        # Sort by interval for chronological order
        five_min_intervals = five_min_intervals.sort_index()
        
        # Convert interval to readable time format for x-axis
        interval_labels = [f"{m//60:02d}:{m%60:02d}" for m in five_min_intervals.index]
        
        # Plot the data
        plt.bar(range(len(five_min_intervals)), five_min_intervals.values, color='coral')
        
        # Set x-axis ticks and labels (showing fewer labels to avoid crowding)
        tick_spacing = max(1, len(five_min_intervals) // 15)  # Show ~15 labels at most
        plt.xticks(
            range(0, len(five_min_intervals), tick_spacing),
            [interval_labels[i] for i in range(0, len(five_min_intervals), tick_spacing)],
            rotation=45
        )
        
        plt.title('Comments by 5-Minute Intervals')
        plt.xlabel('Stream Time (HH:MM)')
        plt.ylabel('Number of Comments')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{video_id}_five_minute_intervals.png"))
        plt.close()
    
    print(f"Visualizations saved to {output_dir}")

def print_analysis_summary(analysis, file_name):
    """Print a summary of the chat analysis."""
    print("\n" + "="*80)
    print(f"CHAT ANALYSIS SUMMARY FOR: {os.path.basename(file_name)}")
    print("="*80)
    
    print(f"\nTotal Comments: {analysis['total_comments']:,}")
    
    if 'member_percentage' in analysis and analysis['member_percentage'] > 0:
        print(f"Member Comments: {analysis['member_percentage']:.2f}%")
    
    if 'superchat_percentage' in analysis and analysis['superchat_percentage'] > 0:
        print(f"Superchat Comments: {analysis['superchat_percentage']:.2f}%")
    
    print("\nTop 10 Commenters:")
    for _, row in analysis['top_commenters'].iterrows():
        print(f"  - {row['author']}: {row['comment_count']} comments")
    
    if not analysis['five_minute_intervals'].empty:
        print("\nTop 10 5-Minute Intervals with Most Activity:")
        for _, row in analysis['five_minute_intervals'].iterrows():
            print(f"  - {row['time_range']}: {row['comment_count']} comments")
    
    if not analysis['ten_minute_intervals'].empty:
        print("\nTop 10 10-Minute Intervals with Most Activity:")
        for _, row in analysis['ten_minute_intervals'].iterrows():
            print(f"  - {row['time_range']}: {row['comment_count']} comments")
    
    print("\nTop 10 Comments (by length):")
    for idx, row in enumerate(analysis['top_comments'].itertuples(), 1):
        print(f"  {idx}. [{row.timestamp_text}] {row.author}: {row.message[:50]}..." if len(row.message) > 50 else f"  {idx}. [{row.timestamp_text}] {row.author}: {row.message}")
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80 + "\n")

def save_analysis_results(analysis, file_name, output_dir):
    """Save analysis results to CSV files."""
    analysis_dir = os.path.join(output_dir, "analysis")
    if not os.path.exists(analysis_dir):
        os.makedirs(analysis_dir)
    
    # Base name for output files
    base_name = os.path.splitext(os.path.basename(file_name))[0]
    
    # Save top commenters
    analysis['top_commenters'].to_csv(os.path.join(analysis_dir, f"{base_name}_top_commenters.csv"), index=False)
    
    # Save interval data if available
    if not analysis['five_minute_intervals'].empty:
        analysis['five_minute_intervals'].to_csv(os.path.join(analysis_dir, f"{base_name}_five_minute_intervals.csv"), index=False)
    
    if not analysis['ten_minute_intervals'].empty:
        analysis['ten_minute_intervals'].to_csv(os.path.join(analysis_dir, f"{base_name}_ten_minute_intervals.csv"), index=False)
    
    # Save top comments
    analysis['top_comments'].to_csv(os.path.join(analysis_dir, f"{base_name}_top_comments.csv"), index=False)
    
    # Save overall summary
    summary = {
        "total_comments": analysis["total_comments"],
        "member_percentage": analysis["member_percentage"],
        "superchat_percentage": analysis["superchat_percentage"]
    }
    
    with open(os.path.join(analysis_dir, f"{base_name}_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Analysis results saved to {analysis_dir}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Analyze YouTube live chat from JSON files")
    parser.add_argument("json_file", help="Path to JSON file with chat data")
    parser.add_argument("-o", "--output-dir", default=".", 
                        help="Output directory for analysis results (default: current directory)")
    parser.add_argument("--no-visualizations", action="store_true",
                        help="Skip generating visualizations")
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.json_file):
        print(f"Error: File not found: {args.json_file}")
        sys.exit(1)
    
    # Load and analyze chat data
    df = load_chat_data(args.json_file)
    
    if not df.empty:
        # Analyze the chat data
        analysis = analyze_chat_data(df)
        
        # Print analysis summary
        print_analysis_summary(analysis, args.json_file)
        
        # Save analysis results
        save_analysis_results(analysis, args.json_file, args.output_dir)
        
        # Generate visualizations
        if not args.no_visualizations:
            generate_visualizations(df, args.json_file, args.output_dir)
    
    print("\nDone! Live chat data has been analyzed.")

if __name__ == "__main__":
    main()