import os
from dotenv import load_dotenv, find_dotenv

# --- Load .env before any imports that use env ---
dotenv_path = find_dotenv(usecwd=True)
if not dotenv_path:
    raise RuntimeError("Could not find a .env file in the current working directory.")
load_dotenv(dotenv_path, override=True)

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
    """
    If LangGraph returned an empty state (or anything odd), run the same steps
    procedurally so you still get a valid email.
    """
    s = {}
    s = load_sources(s)         # -> sets sources, fetched=[], new_items=[]
    s = fetch_all(s)            # -> fills fetched
    s = detect_new(s)           # -> fills new_items
    s = build_email(s)          # -> sets email_html + subject
    return s

if __name__ == "__main__":
    # 1) Try graph pipeline
    state = {}
    try:
        state = run_graph_and_return_state()
    except Exception as e:
        print("[debug] graph pipeline error:", repr(e))

    # 2) If the graph returned nothing, use the fallback (same logic, no graph)
    if not state or "email_html" not in state or "subject" not in state:
        print("[debug] graph state empty; running fallback")
        try:
            state = run_fallback_procedural()
        except Exception as e:
            print("[debug] fallback error:", repr(e))
            state = {}

    # 3) Final safety
    html = state.get("email_html", "<p>No new updates today (but state was empty).</p>")
    subject = state.get("subject", "Competitor Watcher · (fallback)")

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    if dry_run:
        print("[debug] subject:", subject)
        print("[debug] html length:", len(html))
        print(html)
    else:
        send_email(subject, html)
        print("Email sent.")