# UNDP Futures Trends & Signals Platform - Email System

## Overview

The UNDP Future Trends & Signals platform includes functionality to send weekly digest emails containing summaries of recently published signals. This email system keeps curators and other stakeholders informed about new content without requiring them to regularly visit the platform.

## Components

The email system consists of the following components:

1. **Email Service Architecture**
   - `EmailServiceBase`: Abstract base class defining the interface for all email services
   - `MSGraphEmailService`: Implementation using Microsoft Graph API with enterprise application authentication
   - `UserAuthEmailService`: Implementation using Azure CLI authentication
   - `EmailFactory`: Factory pattern for creating the appropriate service based on configuration

2. **Weekly Digest Feature**
   - `WeeklyDigestService`: Core service that fetches recent signals and generates digest emails
   - HTML email template with responsive design for signal summaries
   - Filtering for approved/published signals within a specified date range

3. **Testing Tools**
   - `send_digest.py`: CLI script for sending weekly digests with parameterized options
   - `test_email_direct.py`: Script for testing email configuration without database dependencies

## Setup and Configuration

### Requirements

1. Install the required Python packages:

```bash
# Activate your virtual environment
source venv/bin/activate

# Install the required packages
pip install python-dotenv msgraph-core azure-identity httpx
```

### Environment Variables

The following environment variables need to be set in your `.env.local` file:

```
# Email Configuration
MS_FROM_EMAIL=exo.futures.curators@undp.org  # Email that will appear as the sender
EMAIL_SERVICE_TYPE=ms_graph                  # Authentication type (ms_graph or user_auth)

# Azure Authentication for UNDP Enterprise Application
TENANT_ID=b3e5db5e-2944-4837-99f5-7488ace54319  # UNDP tenant ID
CLIENT_ID=4b179bfc-6621-409a-a1ed-ad141c12eb11  # UNDP Future Trends and Signals System App ID
CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE           # Generate this in Azure Portal
```

### Authentication Methods

The platform supports multiple authentication methods for sending emails:

#### 1. Enterprise Application Authentication (Recommended for Production)

This method uses an Azure AD enterprise application with client credentials flow to authenticate and send emails on behalf of a mailbox.

Requirements:
- UNDP Enterprise Application "UNDP Future Trends and Signals System"
- App ID: `4b179bfc-6621-409a-a1ed-ad141c12eb11`
- Tenant ID: `b3e5db5e-2944-4837-99f5-7488ace54319` (UNDP tenant)
- Client Secret (generated in Azure Portal)
- Mail.Send API permissions granted to the application

This is the recommended approach for production as it doesn't require user presence and provides a more secure, managed identity for the application.

#### 2. User Authentication (For Development)

This method uses the Azure CLI authentication that's already set up on your machine. This is easier for development and testing as it doesn't require setting up app registrations or API credentials.

Requirements:
- Azure CLI installed and logged in with `az login`
- User must have Mail.Send permissions in Microsoft Graph


### Azure AD Enterprise Application Configuration

To configure the enterprise application for sending emails:

1. Sign in to the [Azure Portal](https://portal.azure.com)
2. Navigate to "Azure Active Directory" > "App registrations"
3. Search for "UNDP Future Trends and Signals System" (App ID: `4b179bfc-6621-409a-a1ed-ad141c12eb11`)
4. Under "Certificates & secrets", create a new client secret:
   - Click "New client secret"
   - Provide a description (e.g., "Email Sending Service")
   - Set an appropriate expiration (e.g., 1 year, 2 years)
   - Copy the generated secret value (only shown once)
5. Under "API permissions", verify the following permissions:
   - Microsoft Graph > Application permissions > Mail.Send
   - Microsoft Graph > Application permissions > User.Read.All (for accessing user profiles)
6. Ensure admin consent has been granted for these permissions
7. Update your `.env.local` file with the client secret

## Using the Weekly Digest Feature

### Manual Testing

To send a test digest email:

```bash
# Test with enterprise application authentication
python scripts/test_email_direct.py recipient@example.com

# Test weekly digest
python scripts/send_digest.py --recipients recipient@example.com --days 7 --test
```

Parameters:
- `--recipients`: One or more email addresses (space-separated)
- `--days`: Number of days to look back for signals (default: 7)
- `--test`: Adds [TEST] to the email subject

### Production Scheduling

For regular weekly emails, set up a cron job or Azure scheduled task:

```bash
# Example cron job (every Monday at 8am)
0 8 * * 1 /path/to/python /path/to/scripts/send_digest.py --recipients email1@undp.org email2@undp.org
```

## Customization

### Email Templates

The HTML email template is embedded in the `generate_email_html` method of the `WeeklyDigestService` class. To customize:

1. Modify the HTML structure in the method
2. Update CSS styles to match UNDP branding guidelines
3. Adjust the content formatting as needed

### Recipients Management

Currently, recipients are specified manually when calling the script. Future enhancements could include:

- Storing recipient lists in the database
- Building a subscription management UI
- Supporting user-specific preferences for digest contents

## Troubleshooting

### Permission Issues

If you encounter "Access Denied" errors when sending emails:

1. Check that the enterprise application has the necessary Mail.Send permissions
2. Ensure the permissions have been granted admin consent
3. Verify that the sender email matches an email address the application has permission to send from

### Common Issues and Solutions

1. **401 Unauthorized Error**
   - Check that client secret is valid and not expired
   - Ensure TENANT_ID and CLIENT_ID are correct

2. **403 Forbidden Error**
   - Check that the enterprise application has been granted proper permissions
   - Ensure permissions have been admin consented
   - Verify that the sender email has proper mailbox permissions

3. **Connection Issues**
   - Check network connectivity
   - Ensure firewall rules allow outbound connections to graph.microsoft.com

4. **Email Delivery Problems**
   - Verify that the sender email address is configured correctly
   - Check if the email address has sending limits or restrictions

For detailed error logging, set `LOGLEVEL=DEBUG` in your environment variables.

## Planned Enhancements

### Near-term

1. Set up scheduled task for automated weekly emails
2. Configure environment variables in production environment
3. Implement more sophisticated email templates

### Future Enhancements

1. **Recipient Management**
   - Database table for storing subscriber information
   - API endpoints for subscribing/unsubscribing
   - User preferences for digest frequency and content

2. **Email Customization**
   - Different email templates for different types of notifications
   - Personalized content based on user interests or roles
   - Multiple language support

3. **Analytics**
   - Tracking email opens and clicks
   - Reporting on engagement metrics
   - A/B testing of email content and formats