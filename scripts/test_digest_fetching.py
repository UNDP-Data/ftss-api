#!/usr/bin/env python
"""
Script to test the weekly digest signal fetching and HTML generation without sending emails.
This helps verify that the core digest functionality is working properly.
"""

import os
import sys
import asyncio
import argparse
import logging
import json
from typing import List
from datetime import datetime

# Add the parent directory to sys.path to allow importing the app modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

try:
    from dotenv import load_dotenv
except ImportError:
    # Define a simple fallback if python-dotenv is not installed
    def load_dotenv(path):
        print(f"Warning: python-dotenv package not installed, loading environment manually")
        if not os.path.exists(path):
            return False
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")
        return True

# Load environment variables from .env
env_file = os.path.join(parent_dir, '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded environment from {env_file}")
else:
    print(f"Warning: {env_file} not found")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the weekly digest service
from src.services.weekly_digest import WeeklyDigestService

async def test_digest_fetching(days: int = 7, save_to_file: bool = True, output_path: str = None) -> None:
    """
    Test fetching recent signals and generating a digest without sending an email.
    
    Parameters
    ----------
    days : int, optional
        Number of days to look back for signals, defaults to 7.
    save_to_file : bool, optional
        Whether to save the generated HTML to a file, defaults to True.
    output_path : str, optional
        Path to save the output HTML, defaults to 'digest_output.html' in the current directory.
    """
    print("\n=====================================================")
    print(f"🔍 TESTING WEEKLY DIGEST SIGNAL FETCHING")
    print(f"Looking back {days} days for signals...")
    print("=====================================================\n")
    
    try:
        # Create the digest service
        digest_service = WeeklyDigestService()
        
        # Get recent signals 
        signals_list = await digest_service.get_recent_signals(days)
        
        # Print signal count and basic info
        if signals_list:
            print(f"\n✅ Successfully retrieved {len(signals_list)} signals from the last {days} days.")
            print("\nSignals Summary:")
            print("-" * 60)
            
            for i, signal in enumerate(signals_list, 1):
                print(f"{i}. {signal.headline}")
                print(f"   Created: {signal.created_at}")
                print(f"   Location: {signal.location or 'Global'}")
                if hasattr(signal, 'keywords') and signal.keywords:
                    print(f"   Keywords: {', '.join(signal.keywords)}")
                print(f"   Status: {signal.status}")
                print("-" * 60)
            
            # Generate HTML content
            print("\nGenerating HTML digest content...")
            html_content = digest_service.generate_email_html(signals_list)
            
            # Save HTML to file if requested
            if save_to_file:
                if output_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = os.path.join(os.path.dirname(__file__), f"digest_output_{timestamp}.html")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
                print(f"\n✅ HTML digest content saved to: {output_path}")
                print("   You can open this file in a browser to preview the digest email.")
                
            # Save signals to JSON for debugging
            json_path = os.path.join(os.path.dirname(__file__), "signals_data.json")
            
            signals_data = []
            for signal in signals_list:
                # Convert to dict and handle datetime objects for JSON serialization
                signal_dict = signal.model_dump()
                
                # Convert datetime objects to strings
                for key, value in signal_dict.items():
                    if isinstance(value, datetime):
                        signal_dict[key] = value.isoformat()
                        
                signals_data.append(signal_dict)
                
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(signals_data, f, indent=2)
                
            print(f"📊 Signal data saved to: {json_path}")
            
        else:
            print(f"\n⚠️ No signals found in the last {days} days.")
            print("   This could be because:")
            print("   - There are no approved signals in the database")
            print("   - The signals were created before the specified time period")
            print("   - There might be an issue with the database connection")
            
    except Exception as e:
        import traceback
        logger.error(f"Error while testing digest fetching: {str(e)}")
        traceback.print_exc()
        print(f"\n❌ Error testing digest functionality: {str(e)}")

def main() -> None:
    """Parse command line arguments and run the digest test."""
    parser = argparse.ArgumentParser(description="Test weekly digest signal fetching and HTML generation")
    
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for signals (default: 7)"
    )
    
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save the generated HTML to a file"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save the output HTML (default: digest_output_TIMESTAMP.html in current directory)"
    )
    
    args = parser.parse_args()
    
    # Run the async function
    asyncio.run(test_digest_fetching(
        days=args.days, 
        save_to_file=not args.no_save,
        output_path=args.output
    ))

if __name__ == "__main__":
    main()