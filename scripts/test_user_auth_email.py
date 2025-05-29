#!/usr/bin/env python
"""
Test script for sending emails using user authentication with Azure CLI.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

# Load environment variables
env_file = os.path.join(parent_dir, '.env.local')
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"Loaded environment from {env_file}")
else:
    print(f"Warning: {env_file} not found")

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def test_email(to_email: str) -> None:
    """Send a test email using the email service factory"""
    try:
        from src.services.email_factory import create_email_service
        
        print(f"\nSending test email to {to_email}...")
        
        # Create the email service
        email_service = create_email_service()
        logger.info(f"Email service created: {type(email_service).__name__}")
        
        # Create HTML content with current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>UNDP Futures - User Auth Test Email</title>
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
                <h1>UNDP Futures - User Auth Test Email</h1>
            </div>
            
            <div class="content">
                <h2>User Authentication Email Test</h2>
                <p>This is a test email sent using Azure CLI user authentication.</p>
                <p>If you're receiving this, it means the email configuration is working!</p>
                <p>Sent at: {timestamp}</p>
                <p>Configuration:</p>
                <ul>
                    <li>From Email: {os.getenv('MS_FROM_EMAIL')}</li>
                    <li>User Email: {os.getenv('USER_EMAIL')}</li>
                    <li>To Email: {to_email}</li>
                    <li>Tenant ID: {os.getenv('TENANT_ID')}</li>
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
        success = await email_service.send_email(
            to_emails=[to_email],
            subject=f"[TEST] UNDP Futures - User Auth Email Test ({timestamp})",
            content=html_content,
            content_type="text/html"
        )
        
        if success:
            print("\n=====================================================")
            print(f"✅ Test email successfully sent to {to_email}!")
            print("=====================================================\n")
        else:
            print("\n=====================================================")
            print(f"❌ Failed to send test email to {to_email}")
            print("=====================================================\n")
            
    except Exception as e:
        logger.error(f"Error in test_email: {str(e)}", exc_info=True)
        print("\n=====================================================")
        print(f"❌ Error sending test email: {str(e)}")
        print("=====================================================\n")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_user_auth_email.py <recipient_email>")
        sys.exit(1)
        
    recipient_email = sys.argv[1]
    asyncio.run(test_email(recipient_email))

if __name__ == "__main__":
    main()