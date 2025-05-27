# Enabling Automated Email Sending via Microsoft Graph

To allow the Future of Development platform to send emails automatically (e.g., for digests, notifications) without manual authentication, you must configure Microsoft Graph **Application permissions** for your Azure AD app registration.

## Why Application Permissions?
- **Delegated permissions** require a user to be logged in interactively—this is not suitable for scheduled/automated jobs.
- **Application permissions** allow your backend/server to send emails as a service account using only a client ID and secret.

## Steps for Admin

1. **Go to Azure Portal > Azure Active Directory > App registrations > [Your App]**
2. **API permissions**:
    - Click **Add a permission** > **Microsoft Graph** > **Application permissions**
    - Search for and add **Mail.Send** (Application)
3. **Grant admin consent**:
    - Click **Grant admin consent for [Your Org]**
4. **Verify**:
    - You (or your admin) can run:
      ```sh
      az ad app permission list --id <client-id>
      ```
      - You should see a `"type": "Role"` for Mail.Send.

## Template Email/Message to Admin

```
Subject: Request: Grant Application Mail.Send Permission to Azure App for Automated Email Sending

Hi [Admin],

We need to enable automated email sending from the "Future of Development" app (Client ID: 4b179bfc-6621-409a-a1ed-ad141c12eb11) using Microsoft Graph.

**Please:**
1. Go to Azure Portal > Azure Active Directory > App registrations > "Future of Development".
2. Under **API permissions**, click **Add a permission** > **Microsoft Graph** > **Application permissions**.
3. Add **Mail.Send** (Application).
4. Click **Grant admin consent for [Your Org]**.

This will allow our backend to send emails on a schedule without manual login.

Thank you!
```

## After Admin Consent
- You can now use the client ID, tenant ID, and client secret to send emails via Microsoft Graph API using `/users/{user_id}/sendMail`.
- No manual login will be required for scheduled jobs.

---

**If you need to check the current permissions or verify setup, use:**
```sh
az ad app permission list --id <client-id>
```

--- 