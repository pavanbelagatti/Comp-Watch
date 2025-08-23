import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email

def _get_env(name: str, default: str | None = None) -> str:
    val = os.getenv(name)
    if val is None:
        if default is None:
            raise RuntimeError(f"Missing required env var: {name}")
        return default
    val = val.strip()
    if not val:
        if default is None:
            raise RuntimeError(f"Missing required env var: {name}")
        return default
    return val

def send_email(subject: str, html: str):
    """Send email using SendGrid only (env read at call time)."""
    to_email = _get_env("TO_EMAIL")
    from_email = _get_env("FROM_EMAIL")
    sender_name = _get_env("EMAIL_SENDER_NAME", "Competitor Watcher")
    sg_key = _get_env("SENDGRID_API_KEY")

    message = Mail(
        from_email=Email(from_email, sender_name),  # must be verified in SendGrid
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
    sg = SendGridAPIClient(sg_key)
    sg.send(message)