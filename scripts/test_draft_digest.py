#!/usr/bin/env python
"""
Script to test fetching draft signals and generating a digest.
"""

import os
import sys
import asyncio
import argparse
import logging
import json
from typing import List
from datetime import datetime
import time

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

# Import the draft digest service
from src.services.draft_digest import DraftDigestService
from src.services.email_factory import create_email_service
from src.entities import Status

async def test_draft_digest(days: int = 7, save_to_file: bool = True, output_path: str = None, send_email: bool = False, recipient_email: str = "andrew.maguire@undp.org") -> None:
    """
    Test fetching DRAFT signals and generating a digest.
    
    Parameters
    ----------
    days : int, optional
        Number of days to look back for signals, defaults to 7.
    save_to_file : bool, optional
        Whether to save the generated HTML to a file, defaults to True.
    output_path : str, optional
        Path to save the output HTML, defaults to 'draft_digest_output.html' in the current directory.
    send_email : bool, optional
        Whether to send the digest via email, defaults to False.
    recipient_email : str, optional
        Email address to send the digest to, defaults to "andrew.maguire@undp.org".
    """
    print("\n=====================================================")
    print(f"🔍 TESTING DRAFT SIGNAL DIGEST")
    print(f"Looking back {days} days for draft signals...")
    print("=====================================================\n")
    
    try:
        # Create the digest service
        digest_service = DraftDigestService()
        
        # Set title
        title = "Draft Signals Digest"
        
        # Get draft signals
        signals_list = await digest_service.get_recent_draft_signals(days)
        
        # Print signal count and basic info
        if signals_list:
            print(f"\n✅ Successfully retrieved {len(signals_list)} DRAFT signals from the last {days} days.")
            print("\nSignals Summary:")
            print("-" * 60)
            
            for i, signal in enumerate(signals_list, 1):
                print(f"{i}. {signal.headline}")
                print(f"   Created: {signal.created_at}")
                print(f"   Status: {signal.status}")
                print(f"   Created by: {getattr(signal, 'created_by', 'Unknown')}")
                print(f"   Location: {signal.location or 'Global'}")
                if hasattr(signal, 'keywords') and signal.keywords:
                    print(f"   Keywords: {', '.join(signal.keywords)}")
                print("-" * 60)
            
            # Generate HTML content
            print(f"\nGenerating HTML digest content for draft signals...")
            html_content = digest_service.generate_digest_html(
                signals_list, 
                title=title,
                intro_text=f"<p>Here's a digest of draft signals from the last {days} days:</p>"
            )
            
            # Save HTML to file if requested
            if save_to_file:
                if output_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = os.path.join(os.path.dirname(__file__), f"draft_digest_{timestamp}.html")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
                print(f"\n✅ HTML digest content saved to: {output_path}")
                print("   You can open this file in a browser to preview the digest.")
                
            # Save signals to JSON for debugging
            json_path = os.path.join(os.path.dirname(__file__), f"draft_signals_data.json")
            
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
            
            # Send email if requested
            if send_email and html_content:
                print(f"\n📧 Sending draft digest email to {recipient_email}...")
                try:
                    # Create email service
                    email_service = create_email_service()
                    
                    # Generate subject with timestamp
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    subject = f"[TEST] UNDP Future Trends - Draft Signals Digest ({timestamp})"
                    
                    # Send the email
                    success = await email_service.send_email(
                        to_emails=[recipient_email],
                        subject=subject,
                        content=html_content,
                        content_type="text/html"
                    )
                    
                    if success:
                        print(f"✅ Draft digest email successfully sent to {recipient_email}")
                    else:
                        print(f"❌ Failed to send draft digest email to {recipient_email}")
                        
                except Exception as e:
                    logger.error(f"Error sending email: {str(e)}")
                    print(f"❌ Error sending email: {str(e)}")
            
        else:
            print(f"\n⚠️ No draft signals found in the last {days} days.")
            print("   This could be because:")
            print(f"   - There are no draft signals in the database")
            print("   - The signals were created before the specified time period")
            print("   - There might be an issue with the database connection")
            
            if send_email:
                print("\n📧 Not sending email because no signals were found.")
            
    except Exception as e:
        import traceback
        logger.error(f"Error while testing draft digest: {str(e)}")
        traceback.print_exc()
        print(f"\n❌ Error testing draft digest functionality: {str(e)}")

def main() -> None:
    """Parse command line arguments and run the draft digest test."""
    parser = argparse.ArgumentParser(description="Test fetching draft signals and generating a digest")
    
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
        help="Path to save the output HTML (default: draft_digest_TIMESTAMP.html in current directory)"
    )
    
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send the digest via email to the specified recipient"
    )
    
    parser.add_argument(
        "--recipient",
        type=str,
        default="andrew.maguire@undp.org",
        help="Email address to send the digest to (default: andrew.maguire@undp.org)"
    )
    
    args = parser.parse_args()
    
    # Run the async function
    asyncio.run(test_draft_digest(
        days=args.days,
        save_to_file=not args.no_save,
        output_path=args.output,
        send_email=args.email,
        recipient_email=args.recipient
    ))

if __name__ == "__main__":
    main()