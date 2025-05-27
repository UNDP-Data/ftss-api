# Email Service Configuration

This document explains how to set up and use the email service with Microsoft Graph API and the Mail.Send permission.

## Requirements

To use the email service with Microsoft Graph API, you need:

1. An Azure AD application registration with the following delegated permissions:
   - `Mail.Send`
   - `User.Read`

2. The following environment variables:
   - `MS_FROM_EMAIL`: The email address that will be used as the sender
   - `EMAIL_SERVICE_TYPE`: The type of email service to use (default: `ms_graph`)

## Configuration

### Setting Up the Email Service

The application uses a factory pattern to create the appropriate email service. By default, it uses the Microsoft Graph API with the `Mail.Send` permission.

```python
# The factory creates the appropriate email service based on the environment variables
from src.services.email_factory import create_email_service

# Create an email service instance
email_service = create_email_service()
```

### Environment Variables

Configure the following environment variables:

```bash
# Required for Microsoft Graph Email Service
MS_FROM_EMAIL=your-sender-email@example.com
EMAIL_SERVICE_TYPE=ms_graph  # Options: ms_graph, sendgrid
```

## Usage Examples

### Sending a Simple Email

```python
from src.services.email_factory import create_email_service

# Create an email service instance
email_service = create_email_service()

# Send an email
await email_service.send_email(
    to_emails=["recipient@example.com"],
    subject="Test Subject",
    content="This is the email content",
    content_type="text/plain"  # or "text/html" for HTML content
)
```

### Sending a Templated Notification Email

```python
from src.services.email_factory import create_email_service

# Create an email service instance
email_service = create_email_service()

# Send a notification email using a template
await email_service.send_notification_email(
    to_email="recipient@example.com",
    subject="Notification Subject",
    template_id="welcome-template",
    dynamic_data={
        "name": "John Doe",
        "organization": "UNDP",
        "role": "Admin"
    }
)
```

## Testing the Email Service

You can test the email service by running the provided test script:

```bash
# Make the script executable
chmod +x test_mail_send.py

# Run the test script
./test_mail_send.py
```

The script will prompt you to enter a recipient email address and will send a test email to verify that the `Mail.Send` permission is working correctly.

## Troubleshooting

If you encounter issues with sending emails:

1. Verify that the Azure AD application has the required permissions (Mail.Send and User.Read)
2. Ensure that the permissions have been admin-consented
3. Check that the MS_FROM_EMAIL environment variable is set correctly
4. Check the application logs for detailed error messages
5. Verify that the DefaultAzureCredential is properly configured 