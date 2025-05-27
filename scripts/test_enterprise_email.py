#!/usr/bin/env python
"""
Script to test email sending using enterprise application authentication.
This is useful for verifying that the enterprise app credentials are properly set up.
"""

import os
import sys
import asyncio
import logging
import traceback
from typing import List
from datetime import datetime
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

# Check if required environment variables are set for enterprise application authentication 
required_vars = ["MS_FROM_EMAIL", "TENANT_ID", "CLIENT_ID", "CLIENT_SECRET"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"ERROR: The following required environment variables are not set: {', '.join(missing_vars)}")
    print("These are required for enterprise application authentication.")
    print("Please check your .env.local file and ensure you've generated a CLIENT_SECRET in the Azure Portal.")
    sys.exit(1)

# Set EMAIL_SERVICE_TYPE to ms_graph to force using the enterprise app authentication
os.environ["EMAIL_SERVICE_TYPE"] = "ms_graph"
print("Force setting EMAIL_SERVICE_TYPE to 'ms_graph' for enterprise application authentication")

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

async def test_enterprise_email(to_email: str) -> None:
    """
    Send a test email using the enterprise application authentication.
    
    Parameters
    ----------
    to_email : str
        The email address to send the test email to.
    """
    logger.info("="*80)
    logger.info("ENTERPRISE APPLICATION EMAIL TEST")
    logger.info("="*80)
    logger.info(f"Starting enterprise authentication email test to {to_email}")
    logger.info(f"From email: {os.getenv('MS_FROM_EMAIL')}")
    logger.info(f"Tenant ID: {os.getenv('TENANT_ID')}")
    logger.info(f"Client ID: {os.getenv('CLIENT_ID')}")
    logger.info(f"Client Secret: {'*' * 8} (hidden for security)")
    
    # Create the email service
    try:
        from src.services.email_factory import create_email_service
        from src.services.msgraph_service import MSGraphEmailService
        
        email_service = create_email_service()
        
        # Verify that we got an MSGraphEmailService instance
        if not isinstance(email_service, MSGraphEmailService):
            logger.error(f"Expected MSGraphEmailService, but got {type(email_service).__name__}")
            print("\n=====================================================")
            print("❌ Wrong email service type created. Check EMAIL_SERVICE_TYPE setting.")
            print("=====================================================\n")
            return
            
        logger.info(f"Email service created: {type(email_service).__name__}")
    except Exception as e:
        logger.error(f"Failed to create email service: {e}")
        traceback.print_exc()
        return
    
    # Create a simple HTML email with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UNDP Futures - Enterprise App Email Test</title>
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
            <h1>UNDP Futures - Enterprise App Test</h1>
        </div>
        
        <div class="content">
            <h2>Enterprise Application Email Test</h2>
            <p>This is a test email to verify that email sending via enterprise application authentication is working correctly.</p>
            <p>If you're receiving this, it means the enterprise application credentials are properly set up!</p>
            <p>Sent at: {timestamp}</p>
            <p>Configuration:</p>
            <ul>
                <li>Authentication: Enterprise Application</li>
                <li>App Name: UNDP Future Trends and Signals System</li>
                <li>App ID: {os.getenv('CLIENT_ID')}</li>
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
        logger.info("Attempting to send email using enterprise application authentication...")
        success = await email_service.send_email(
            to_emails=[to_email],
            subject=f"[TEST] UNDP Futures - Enterprise Application Email Test",
            content=html_content,
            content_type="text/html"
        )
        
        if success:
            logger.info("✅ Test email sent successfully using enterprise application authentication!")
            print("\n=====================================================")
            print(f"✅ Test email sent successfully to {to_email}!")
            print("The enterprise application authentication is working correctly.")
            print("=====================================================\n")
        else:
            logger.error("❌ Failed to send test email using enterprise application authentication")
            print("\n=====================================================")
            print(f"❌ Failed to send test email to {to_email}")
            print("Check the logs for more details.")
            print("=====================================================\n")
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        traceback.print_exc()
        print("\n=====================================================")
        print(f"❌ Error sending test email to {to_email}: {e}")
        print("=====================================================\n")

def main() -> None:
    """Parse command line arguments and run the enterprise email test."""
    if len(sys.argv) < 2:
        print("Usage: python test_enterprise_email.py <recipient_email>")
        sys.exit(1)
    
    recipient_email = sys.argv[1]
    
    # Validate email address (basic check)
    if "@" not in recipient_email:
        logger.error(f"Invalid email address: {recipient_email}")
        sys.exit(1)
    
    # Run the async function
    asyncio.run(test_enterprise_email(recipient_email))

if __name__ == "__main__":
    main()