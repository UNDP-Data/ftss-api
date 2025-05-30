# Support Ticket: Enable Automated Email Sending for Future of Development Platform

**Subject:**
Enable Automated Email Sending for Future Trends & Signals (Microsoft Graph Application Permissions)

**Description:**
We are building a feature for the Future of Development platform that sends automated email digests (e.g., weekly summaries, notifications) to users. To do this securely and reliably, we need to configure Microsoft Graph **Application permissions** for our Azure AD app registration, and set up a dedicated internal email account for sending these digests.

## Requirements

1. **Azure AD App Registration:**
    - App Name: **Future Trends & Signals**
    - Client ID: `4b179bfc-6621-409a-a1ed-ad141c12eb11`
    - The app must be able to send emails automatically (without manual login) using Microsoft Graph.

2. **Permissions Needed:**
    - Add **Mail.Send** (Application) permission to the app registration.
    - Grant **admin consent** for this permission.

3. **Service Account:**
    - Please create or confirm an internal mailbox (e.g., `futureofdevelopment@undp.org`) to be used as the sender for these digests.
    - Ensure this mailbox is licensed and can send emails.

4. **Configuration Steps (for ITU):**
    - Go to Azure Portal > Azure Active Directory > App registrations > "Future of Development".
    - Under **API permissions**, click **Add a permission** > **Microsoft Graph** > **Application permissions**.
    - Add **Mail.Send** (Application).
    - Click **Grant admin consent for [Your Org]**.
    - Confirm that the mailbox `futureofdevelopment@undp.org` is active and can be used by the app for sending emails.

5. **Verification:**
    - After configuration, we will verify by running:
      ```sh
      az ad app permission list --id 4b179bfc-6621-409a-a1ed-ad141c12eb11
      ```
      - We should see a `"type": "Role"` for Mail.Send.

## Why This Is Needed
- Delegated permissions require a user to log in interactively, which is not suitable for scheduled/automated jobs.
- Application permissions allow our backend to send emails on a schedule, securely and without manual intervention.

## What We Need from ITU
- Add and grant the required permissions as described above.
- Confirm the service account is ready and provide any additional configuration details if needed.

Thank you for your support! If you need more technical details, please see the attached documentation or contact our team. 