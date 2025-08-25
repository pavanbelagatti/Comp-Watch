import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email

def _get_env(name: str, default: str | None = None) -> str:
    v = os.getenv(name)
    if v is None or not v.strip():
        if default is None:
            raise RuntimeError(f"Missing required env var: {name}")
        return default
    return v.strip()

def send_email(subject: str, html: str):
    to_email = _get_env("TO_EMAIL")
    from_email = _get_env("FROM_EMAIL")
    sender_name = _get_env("EMAIL_SENDER_NAME", "Competitor Watcher")
    sg_key = _get_env("SENDGRID_API_KEY")

    message = Mail(
        from_email=Email(from_email, sender_name),
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
    sg = SendGridAPIClient(sg_key)
    resp = sg.send(message)

    if os.getenv("DEBUG_EMAIL", "false").lower() == "true":
        try:
            body = resp.body.decode() if hasattr(resp.body, "decode") else resp.body
        except Exception:
            body = "<no-body>"
        print("[sendgrid] status:", resp.status_code)
        print("[sendgrid] x-message-id:", resp.headers.get("X-Message-Id"))
        print("[sendgrid] body:", body)

    if not (200 <= int(resp.status_code) < 300):
        raise RuntimeError(f"SendGrid error {resp.status_code}: {resp.body}")
