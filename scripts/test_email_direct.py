#!/usr/bin/env python
"""
Script to test email sending directly without database interactions.
This is useful for isolating email configuration issues.
"""

import os
import sys
import asyncio
import logging
import traceback
from typing import List
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

# Load environment variables from .env.local if it exists
env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.local')
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded environment from {env_file}")
else:
    print(f"Warning: {env_file} not found")

# Check if required environment variables are set
required_vars = ["MS_FROM_EMAIL", "EMAIL_SERVICE_TYPE", "TENANT_ID", "CLIENT_ID"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"ERROR: The following required environment variables are not set: {', '.join(missing_vars)}")
    print("Please check your .env.local file or set them manually.")
    sys.exit(1)

# Add the parent directory to sys.path to allow importing the app modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Using DEBUG level to see more detailed info
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def test_email_sending(to_email: str) -> None:
    """
    Send a test email directly using the configured email service.
    
    Parameters
    ----------
    to_email : str
        The email address to send the test email to.
    """
    logger.info(f"Starting direct email test to {to_email}")
    logger.info(f"Using email service type: {os.getenv('EMAIL_SERVICE_TYPE')}")
    logger.info(f"From email: {os.getenv('MS_FROM_EMAIL')}")
    
    # Create the email service
    try:
        from src.services.email_factory import create_email_service
        email_service = create_email_service()
        logger.info(f"Email service created: {type(email_service).__name__}")
    except Exception as e:
        logger.error(f"Failed to create email service: {e}")
        traceback.print_exc()
        return
    
    # Create a simple HTML email with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UNDP Futures - Email Test</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #0768AC;
                color: white;
                padding: 20px;
                text-align: center;
                margin-bottom: 20px;
            }}
            .content {{
                padding: 20px;
                background-color: #f5f5f5;
                border-left: 4px solid #0768AC;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #ddd;
                font-size: 0.9em;
                color: #666;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>UNDP Futures - Test Email</h1>
        </div>
        
        <div class="content">
            <h2>Email Functionality Test</h2>
            <p>This is a test email to verify that the email sending functionality is working correctly.</p>
            <p>If you're receiving this, it means the email configuration is properly set up!</p>
            <p>Sent at: {timestamp}</p>
            <p>Configuration:</p>
            <ul>
                <li>Email Service: {os.getenv('EMAIL_SERVICE_TYPE')}</li>
                <li>From Email: {os.getenv('MS_FROM_EMAIL')}</li>
                <li>To Email: {to_email}</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>This is a test email from the UNDP Futures platform.</p>
            <p>&copy; United Nations Development Programme</p>
        </div>
    </body>
    </html>
    """
    
    # Send the email
    try:
        logger.info("Attempting to send email...")
        success = await email_service.send_email(
            to_emails=[to_email],
            subject=f"[TEST] UNDP Futures - Email Configuration Test ({os.getenv('EMAIL_SERVICE_TYPE')})",
            content=html_content,
            content_type="text/html"
        )
        
        if success:
            logger.info("✅ Test email sent successfully!")
            print("\n=====================================================")
            print(f"✅ Test email sent successfully to {to_email}!")
            print("=====================================================\n")
        else:
            logger.error("❌ Failed to send test email")
            print("\n=====================================================")
            print(f"❌ Failed to send test email to {to_email}")
            print("=====================================================\n")
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        traceback.print_exc()
        print("\n=====================================================")
        print(f"❌ Error sending test email to {to_email}: {e}")
        print("=====================================================\n")

def main() -> None:
    """Parse command line arguments and run the email test."""
    if len(sys.argv) < 2:
        print("Usage: python test_email_direct.py <recipient_email>")
        sys.exit(1)
    
    recipient_email = sys.argv[1]
    
    # Validate email address (basic check)
    if "@" not in recipient_email:
        logger.error(f"Invalid email address: {recipient_email}")
        sys.exit(1)
    
    # Run the async function
    asyncio.run(test_email_sending(recipient_email))

if __name__ == "__main__":
    main()