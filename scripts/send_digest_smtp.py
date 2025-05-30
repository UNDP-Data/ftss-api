#!/usr/bin/env python
"""
Script to send a weekly digest email using SMTP (e.g., Office 365, Gmail).
This is for testing SMTP-based delivery to a distribution list or group.
"""

import os
import sys
import asyncio
import argparse
import logging
import smtplib
from email.mime.text import MIMEText
from typing import List

# Add the parent directory to sys.path to allow importing the app modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from src.services.weekly_digest import WeeklyDigestService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def generate_digest_html(days=None, status=None, limit=None):
    digest_service = WeeklyDigestService()
    signals_list = await digest_service.get_recent_signals(days=days, status=status, limit=limit)
    logger.info(f"Fetched {len(signals_list)} signals for digest.")
    html_content = digest_service.generate_email_html(signals_list)
    return html_content

def send_email_smtp(smtp_server, smtp_port, username, password, to_emails, subject, html_content):
    msg = MIMEText(html_content, 'html')
    msg['Subject'] = subject
    msg['From'] = username
    msg['To'] = ', '.join(to_emails)
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(msg['From'], to_emails, msg.as_string())
    logger.info(f"Email sent via SMTP to {to_emails}")

def main():
    parser = argparse.ArgumentParser(description="Send weekly digest email via SMTP")
    parser.add_argument('--recipients', nargs='+', required=True, help="Email addresses to send the digest to (space-separated)")
    parser.add_argument('--days', type=int, default=None, help="Number of days to look back for signals (optional)")
    parser.add_argument('--status', nargs='+', default=None, help="Signal statuses to filter by (e.g. Draft Approved). Optional.")
    parser.add_argument('--limit', type=int, default=None, help="Maximum number of signals to include (optional)")
    parser.add_argument('--smtp-server', type=str, default='smtp.office365.com', help="SMTP server address")
    parser.add_argument('--smtp-port', type=int, default=587, help="SMTP server port")
    parser.add_argument('--smtp-user', type=str, required=True, help="SMTP username (your email)")
    parser.add_argument('--smtp-password', type=str, required=True, help="SMTP password (or app password)")
    parser.add_argument('--test', action='store_true', help="Run in test mode (adds [TEST] to the subject line)")
    args = parser.parse_args()

    subject = "UNDP Futures Weekly Digest"
    if args.test:
        subject = f"[TEST] {subject}"

    # Validate email addresses
    for email in args.recipients:
        if "@" not in email:
            logger.error(f"Invalid email address: {email}")
            sys.exit(1)

    # Map status strings to Status enum if provided
    status_enum = None
    if args.status:
        from src.services.weekly_digest import Status
        status_enum = [Status(s) for s in args.status]

    # Generate digest HTML
    html_content = asyncio.run(generate_digest_html(days=args.days, status=status_enum, limit=args.limit))

    # Send email via SMTP
    send_email_smtp(
        smtp_server=args.smtp_server,
        smtp_port=args.smtp_port,
        username=args.smtp_user,
        password=args.smtp_password,
        to_emails=args.recipients,
        subject=subject,
        html_content=html_content
    )

if __name__ == "__main__":
    main() 