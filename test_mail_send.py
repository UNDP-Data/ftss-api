#!/usr/bin/env python
"""
Test script to verify the email service with Mail.Send permission.
"""

import asyncio
import os
import sys
import logging
import subprocess
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.services.email_factory import create_email_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def check_azure_cli_auth():
    """Check Azure CLI authentication and ensure correct scopes are set."""
    try:
        # Check if Azure CLI is logged in
        process = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if process.returncode != 0:
            print("Azure CLI is not authenticated. Logging in...")
            subprocess.run(
                ["az", "login", "--scope", "https://graph.microsoft.com/.default"],
                check=True
            )
        else:
            # Check if we need to set the correct scope
            print("Azure CLI is authenticated. Ensuring correct scope is set...")
            subprocess.run(
                ["az", "account", "get-access-token", "--scope", "https://graph.microsoft.com/.default"],
                check=True
            )
            
        print("✅ Azure CLI authentication complete with correct scope")
        return True
    except Exception as e:
        print(f"❌ Failed to authenticate with Azure CLI: {str(e)}")
        return False

async def test_mail_send():
    """Test the email service with Mail.Send permission."""
    
    # First check Azure CLI authentication
    if not check_azure_cli_auth():
        return
        
    # Create the email service using the factory
    email_service = create_email_service()
    
    # Define test parameters
    recipient_email = "andrew.maguire@undp.org"
    subject = "Test Email - UNDP Future Trends and Signals System"
    content = """
    This is a test email sent from the UNDP Future Trends and Signals System.
    It verifies that the Mail.Send permission is working correctly.
    
    If you received this email, the Mail.Send permission is properly configured.
    """
    
    # Send the test email
    print(f"Sending test email to {recipient_email}...")
    result = await email_service.send_email(
        to_emails=[recipient_email],
        subject=subject,
        content=content,
        content_type="text/plain"
    )
    
    # Check the result
    if result:
        print("✅ Test email sent successfully!")
        print("The Mail.Send permission is working correctly.")
    else:
        print("❌ Failed to send test email.")
        print("Check logs for more details.")

if __name__ == "__main__":
    asyncio.run(test_mail_send()) 