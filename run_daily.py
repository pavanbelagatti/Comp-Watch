import os
from dotenv import load_dotenv, find_dotenv

# Load .env if present (CI uses env vars)
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path, override=False)

from app.storage import reset_db_if_requested
from app.graph import load_sources, fetch_all, detect_new, build_email
from app.emailer import send_email

def run_pipeline() -> dict:
    s: dict = {}
    s = load_sources(s)
    s = fetch_all(s)
    s = detect_new(s)
    s = build_email(s)
    return s

if __name__ == "__main__":
    reset_db_if_requested()  # honor RESET_DB_ON_RUN=true
    dry = os.getenv("DRY_RUN", "false").lower() == "true"
    state = run_pipeline()
    html = state.get("email_html", "<p>No output.</p>")
    subject = state.get("subject", "Competitor Watcher")
    if dry:
        print("[debug] subject:", subject)
        print("[debug] html length:", len(html))
        print(html)
    else:
        send_email(subject, html)
        print("Email sent.")
