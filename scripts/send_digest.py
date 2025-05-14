#!/usr/bin/env python
"""
Command-line script to send a weekly digest email.
This script is for manual testing and can be scheduled via cron or other job scheduler.
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import List

# Add the parent directory to sys.path to allow importing the app modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from src.services.weekly_digest import WeeklyDigestService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def send_weekly_digest(recipients: List[str], days: int = 7, test_mode: bool = False) -> None:
    """
    Send a weekly digest email to the specified recipients.
    
    Parameters
    ----------
    recipients : List[str]
        List of email addresses to send the digest to.
    days : int, optional
        Number of days to look back for signals, defaults to 7.
    test_mode : bool, optional
        If True, adds [TEST] to the subject line.
    """
    logger.info(f"Starting weekly digest email send to {recipients}")
    
    # Create the digest service
    digest_service = WeeklyDigestService()
    
    # Prepare subject with test mode indicator if needed
    subject = "UNDP Futures Weekly Digest"
    if test_mode:
        subject = f"[TEST] {subject}"
    
    # Generate and send the digest
    success = await digest_service.generate_and_send_digest(
        recipients=recipients,
        days=days,
        subject=subject
    )
    
    if success:
        logger.info("Weekly digest email sent successfully")
    else:
        logger.error("Failed to send weekly digest email")

def main() -> None:
    """Parse command line arguments and run the digest email process."""
    parser = argparse.ArgumentParser(description="Send weekly digest email of recent signals")
    
    parser.add_argument(
        "--recipients",
        nargs="+",
        required=True,
        help="Email addresses to send the digest to (space-separated)"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for signals (default: 7)"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (adds [TEST] to the subject line)"
    )
    
    args = parser.parse_args()
    
    # Validate email addresses (basic check)
    for email in args.recipients:
        if "@" not in email:
            logger.error(f"Invalid email address: {email}")
            sys.exit(1)
    
    # Run the async function
    asyncio.run(send_weekly_digest(args.recipients, args.days, args.test))

if __name__ == "__main__":
    main()