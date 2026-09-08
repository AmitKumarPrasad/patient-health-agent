# Notifications and reminders

Step 15 adds local appointment reminder delivery using Mailpit. The implementation is provider-agnostic so SMS, WhatsApp, or a transactional email provider can be added later without changing appointment business logic.

## Reminder policy

For appointments at least 24 hours in the future, the system creates two unique email notifications:

- 24 hours before the appointment
- 1 hour before the appointment

A database uniqueness constraint makes reminder scheduling idempotent per appointment, reminder type, and channel.

## Lifecycle behavior

- New scheduled appointments create future reminders automatically.
- Confirming an appointment creates any missing future reminders.
- Cancelled, completed, and no-show appointments suppress pending reminders.
- Failed delivery attempts are persisted with an error message for operator visibility.

## Local verification

Start the stack:

```bash
docker compose up --build
```

Open Mailpit at `http://localhost:8025`.

The admin-only endpoint can process due notifications immediately:

```text
POST /api/admin/notifications/process
Authorization: Bearer <admin-token>
```

For a real-time test, create an appointment whose start time is less than one hour away. The scheduler intentionally does not create reminders whose scheduled time is already in the past.

Use synthetic demo data only. Do not send real patient or clinical information through the local notification system.
