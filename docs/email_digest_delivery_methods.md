# Email Digest Delivery Methods: Summary & Lessons Learned

This document summarizes all the methods we have tried (and considered) for sending automated email digests from the Future Trends & Signals platform, including their outcomes, blockers, and references to official documentation.

---

## 1. Microsoft Graph API (Recommended, but Blocked)

- **Approach:** Use Microsoft Graph API with Application permissions to send as `futureofdevelopment@undp.org`.
- **Status:** **Blocked** (admin consent for Application permissions not yet granted).
- **What we did:**
  - Registered the app in Azure AD.
  - Attempted to use `/users/{user_id}/sendMail` endpoint with client credentials.
  - Only Delegated permissions are currently granted; Application permissions are missing.
- **Blocker:**
  - Cannot send as a service account without `Mail.Send` Application permission and admin consent.
- **Reference:**
  - See [azure_graph_mail_send_setup.md](./azure_graph_mail_send_setup.md) for detailed setup and admin request template.
  - [Microsoft Docs: Send mail as any user](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0&tabs=http)

---

## 2. Microsoft Graph API (Delegated Permissions)

- **Approach:** Use Microsoft Graph API with Delegated permissions, logging in as the sender.
- **Status:** **Not suitable for automation**
- **What we did:**
  - Successfully authenticated as a user and sent test emails using `/me/sendMail`.
- **Blocker:**
  - Requires interactive login; not suitable for scheduled/automated jobs.

---

## 3. SMTP (Office 365/Exchange Online)

- **Approach:** Use SMTP to send as `futureofdevelopment@undp.org` via `smtp.office365.com`.
- **Status:** **Blocked** (SMTP AUTH is disabled for the tenant).
- **What we did:**
  - Created a script (`send_digest_smtp.py`) to send the digest via SMTP.
  - Attempted to authenticate with valid credentials.
  - Received error: `SMTPAuthenticationError: 5.7.139 Authentication unsuccessful, SmtpClientAuthentication is disabled for the Tenant.`
- **Blocker:**
  - SMTP AUTH is disabled for all users by default in modern Microsoft 365 tenants for security reasons.
  - Would require IT to enable SMTP AUTH for the sending account.
- **Reference:**
  - [Enable or disable SMTP AUTH in Exchange Online](https://aka.ms/smtp_auth_disabled)

---

---

## 5. Distribution List/Group Delivery

- **Approach:** Send the digest to a mail-enabled group (`futures.curator@undp.org`).
- **Status:** **Group is mail-enabled and can receive mail**
- **What we did:**
  - Verified the group exists and is mail-enabled in Azure AD.
  - All sending methods above (if working) can target this group.
- **Blocker:**
  - Blocked by the same issues as above (Graph permissions or SMTP AUTH).

---

## **Summary Table**

| Method                | Automation | Current Status         | Blocker/Notes                       |
|-----------------------|------------|-----------------------|--------------------------------------|
| MS Graph (App perms)  | Yes        | Blocked               | Need admin to grant permissions      |
| MS Graph (Delegated)  | No         | Works (manual only)   | Not suitable for automation          |
| SMTP (O365)           | Yes        | Blocked               | SMTP AUTH disabled for tenant        |
| Distribution List     | Yes        | Ready                 | Blocked by above sending method      |

---

## **Next Steps**
- Await admin action to grant Application permissions for Microsoft Graph (see [azure_graph_mail_send_setup.md](./azure_graph_mail_send_setup.md)).
- Alternatively, request IT to enable SMTP AUTH for the sending account (less secure, not recommended).
- Consider third-party relay if allowed by policy.

---

**This document should be updated as our setup or permissions change.** 