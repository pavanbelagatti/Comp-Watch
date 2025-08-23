import os
from dotenv import load_dotenv, find_dotenv

# --- Load .env if present (optional on GitHub Actions) ---
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path, override=False)

# Import AFTER optional .env load so env is ready either way
from langgraph.graph import StateGraph, START, END
from app.graph import load_sources, fetch_all, detect_new, build_email
from app.emailer import send_email


def run_graph_and_return_state() -> dict:
    graph = StateGraph(dict)
    graph.add_node("load_sources", load_sources)
    graph.add_node("fetch_all", fetch_all)
    graph.add_node("detect_new", detect_new)
    graph.add_node("build_email", build_email)

    graph.add_edge(START, "load_sources")
    graph.add_edge("load_sources", "fetch_all")
    graph.add_edge("fetch_all", "detect_new")
    graph.add_edge("detect_new", "build_email")
    graph.add_edge("build_email", END)

    app = graph.compile()
    state = app.invoke({})
    return state if isinstance(state, dict) else {}


def run_fallback_procedural() -> dict:
    """Same steps without LangGraph in case some runtime returns {}."""
    s: dict = {}
    s = load_sources(s)
    s = fetch_all(s)
    s = detect_new(s)
    s = build_email(s)
    return s


if __name__ == "__main__":
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    # 1) Try graph pipeline
    state: dict = {}
    try:
        state = run_graph_and_return_state()
    except Exception as e:
        print("[debug] graph pipeline error:", repr(e))

    # 2) Fallback if needed
    if not state or "email_html" not in state or "subject" not in state:
        print("[debug] graph state empty; running fallback")
        try:
            state = run_fallback_procedural()
        except Exception as e:
            print("[debug] fallback error:", repr(e))
            state = {}

    # 3) Send or print
    html = state.get("email_html", "<p>No new updates today.</p>")
    subject = state.get("subject", "Competitor Watcher")

    if dry_run:
        print(subject)
        print(html)
    else:
        send_email(subject, html)
        print("Email sent.")