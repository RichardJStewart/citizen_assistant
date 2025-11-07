import os
import re
import time
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- Datadog / ddtrace ---
from ddtrace import tracer, patch_all
from ddtrace.llmobs import LLMObs
from ddtrace.llmobs.decorators import workflow, task, agent, tool

# --- LLM client (OpenAI) ---
from openai import OpenAI

# ---------------------------
# 0) Runtime configuration
# ---------------------------
patch_all()  # auto-instrument std libs, HTTP clients, etc.

DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
DD_API_KEY = os.getenv("DD_API_KEY")
DD_APP_KEY = os.getenv("DD_APP_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not DD_API_KEY or not DD_APP_KEY:
    raise RuntimeError("Missing DD_API_KEY or DD_APP_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")

# Enable LLM Observability
LLMObs.enable(
    site=DD_SITE,
    service="citizen-assistant",
    env="demo",
    api_key=DD_API_KEY,
    app_key=DD_APP_KEY,
)
# ---------- Topic + Policy + Retrieval helpers ----------

FEDERAL_TOPICS = {
    "Passports & Travel Documents": ["passport", "state department", "ds-11", "ds-82"],
    "Taxes & IRS Services": ["irs", "tax refund", "income tax", "1040"],
    "Social Security & Benefits": ["ssa", "social security", "ssdi", "ssi"],
    "Medicare & Health Programs": ["medicare", "cms", "part a", "part b", "part d"],
    "Unemployment Insurance (Federal Programs)": ["dol", "federal unemployment", "pua"],
    "Immigration & Citizenship": ["uscis", "citizenship", "naturalization", "green card", "visa"],
    "Veterans Affairs": ["va", "veterans", "gi bill", "va healthcare"],
    "Military & Defense": ["dod", "pentagon", "enlist", "army", "navy", "air force", "marines", "space force"],
    "Small Business & Economic Development": ["sba", "federal loan", "lender match"],
    "Environmental Protection & Energy": ["epa", "environmental violation", "clean air", "clean water"],
    "Disaster Relief & Emergency Management": ["fema", "disaster assistance", "declaration"],
    "Transportation & Travel Safety": ["tsa", "precheck", "global entry", "faa"],
    "Housing & Urban Development": ["hud", "fair housing", "fheo", "fha"],
    "Census & Federal Data": ["census", "data.census.gov"],
    "Voting & Elections (Federal)": ["federal election", "vote.gov", "absentee (federal)"],
}

@task(name="detect_topic")
def detect_topic(text: str) -> str:
    t = text.lower()
    for topic, kws in FEDERAL_TOPICS.items():
        if any(k in t for k in kws):
            return topic
    return "General Federal Inquiry"

@task(name="policy_check")
def policy_check(message: str) -> dict:
    """Very basic moderation stub for demo; extend with your real checks."""
    flagged = contains_pii(message) or any(bad in message.lower() for bad in ["bomb", "attack"])
    return {"flagged": flagged, "reason": "pii_or_disallowed" if flagged else "ok"}

@tool(name="retrieve_docs")
def retrieve_docs(query: str) -> list[str]:
    """Stub: simulate retrieval latency and return fake IDs when relevant."""
    time.sleep(0.02)
    q = query.lower()
    if "passport" in q: return ["faq_passport_renewal", "link_state_dept_ds82"]
    if "irs" in q or "tax" in q: return ["faq_irs_refund", "link_wmr_tool"]
    return []

# Prepare OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are a federal Citizen Services Virtual Assistant. "
    "Answer concisely and accurately based on U.S. federal benefits guidance. "
    "If state/program-specific data is required, state that limits vary by state and point to official resources. "
    "Never invent policy or request/return PII. Do not output SSNs or other sensitive data."
)

# Very simple PII guard for demo purposes
PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN format
    r"\b\d{9}\b",              # 9-digit SSN-like
    r"\b(?:\d[ -]*?){13,16}\b" # CC-like (loose)
]

@task(name="PII_check")
def contains_pii(text: str) -> bool:
    if not text:
        return False
    for pat in PII_PATTERNS:
        if re.search(pat, text):
            return True
    return False

@workflow(name="process_citizen_request")
def process_request(text: str) -> bool:
    if "TRIGGER_AGENT_ERROR" in text:
        return False
    return True

# ---------------------------
# 1) FastAPI app
# ---------------------------
app = FastAPI(title="Citizen Services Virtual Assistant")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve SVG favicon explicitly with correct media type
@app.get("/favicon.ico", include_in_schema=False)
async def favicon_redirect():
    # Some browsers still request /favicon.ico
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    max_tokens: Optional[int] = 300
    temperature: Optional[float] = 0.2


# ---------------------------
# 2) Simple HTML page
# ---------------------------
HTML = """
<!doctype html>
<html>
  <head>
    <link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
    <meta charset="utf-8" />
    <title>Citizen Services Virtual Assistant</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
      body {
        font-family: 'Inter', sans-serif;
        margin: 0;
        padding: 0;
        color: #fff;
        background: linear-gradient(rgba(0, 20, 40, 0.85), rgba(0, 20, 40, 0.85)),
            url('/static/united-state-america-us-usa-banner.jpg')
            no-repeat center center fixed;
        background-size: cover;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .wrap {
        background: rgba(0, 0, 0, 0.6);
        border-radius: 16px;
        padding: 2rem 3rem;
        max-width: 800px;
        width: 90%;
        box-shadow: 0 0 30px rgba(0, 0, 0, 0.4);
      }
      h1 {
        text-align: center;
        font-weight: 600;
        margin-bottom: 0.25rem;
      }
      h1 span {
        color: #32b6ff;
      }
      p.subtitle {
        text-align: center;
        font-size: 1rem;
        opacity: 0.8;
        margin-bottom: 1.5rem;
      }
      textarea {
        width: 100%;
        height: 120px;
        border: none;
        border-radius: 8px;
        padding: 1rem;
        font-size: 1rem;
        resize: none;
        outline: none;
        background: #f9fafb;
        color: #111;
      }
      button {
        display: block;
        margin: 1rem auto 1.5rem;
        background-color: #32b6ff;
        color: white;
        font-weight: 600;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        cursor: pointer;
        font-size: 1rem;
        transition: all 0.2s ease;
      }
      button:hover {
        background-color: #1f9ae2;
        transform: translateY(-1px);
      }
      pre {
        background: #f9fafb;
        color: #111;
        border-radius: 8px;
        padding: 1rem;
        white-space: pre-wrap;
        line-height: 1.5;
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        max-height: 250px;
        overflow-y: auto;
      }
      footer {
        text-align: center;
        font-size: 0.8rem;
        opacity: 0.6;
        margin-top: 1rem;
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <h1><span>Citizen Services</span> Assistant</h1>
      <p class="subtitle">Ask FEDERAL benefit or eligibility questions securely — no personal data needed.</p>
      <textarea id="msg" placeholder="Type your question here..."></textarea>
      <button id="send">Ask</button>
      <pre id="out">(Your AI response will appear here.)</pre>
      <footer>Powered by Datadog LLM Observability & OpenAI</footer>
    </div>

    <script>
      document.getElementById('send').onclick = async () => {
        const msg = document.getElementById('msg').value;
        const res = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        document.getElementById('out').textContent = data.response || data.error || '(no response)';
      };
    </script>
  </body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

# ---------------------------
# 3) Chat endpoint
# ---------------------------
@app.post("/chat")
@agent(name="citizen_agent")
def chat(req: ChatRequest, request: Request):
    user_msg = (req.message or "").strip()

    if not user_msg:
        raise HTTPException(status_code=400, detail="Empty message.")
    if contains_pii(user_msg):
        return JSONResponse(
            status_code=400,
            content={"error": "Your message appears to contain PII. Please remove sensitive information and try again."},
        )

    # If request is to be orchestrated, define logic in process request
    if not process_request(user_msg):
        raise RuntimeError("Synthetic agent failure for demo")

    # Root span (kept the same name so existing dashboards continue to work)
    with tracer.trace("chat.request", service="citizen-assistant", resource="/chat") as root:
        # High-level request metadata
        root.set_tag("app.user_agent", request.headers.get("user-agent", "unknown"))
        root.set_tag("ml.app", "citizen-assistant-chat")
        root.set_tag("ml.provider", "openai")
        root.set_tag("ml.model", OPENAI_MODEL)
        root.set_tag("ml.session_id", req.session_id or "anonymous")
        root.set_tag("ml.temperature", req.temperature)
        root.set_tag("ml.max_tokens", req.max_tokens)
        root.set_tag("ml.prompt_preview", user_msg[:200])

        # --- user interaction (top of the funnel) ---
        with tracer.trace("citizen.user_interaction") as ui:
            ui.set_tag("route", "/chat")
            ui.set_metric("message.length", len(user_msg))

            # topic classification early so it’s queryable on all child spans
            topic = detect_topic(user_msg)
            ui.set_tag("ml.topic", topic)
            root.set_tag("ml.topic", topic)  # duplicate on root for easy filtering

            # --- policy evaluation ---
            with tracer.trace("citizen.policy_evaluation") as pol:
                pol.set_tag("policy.engine", "demo_local_v1")
                polres = policy_check(user_msg)
                pol.set_tag("policy.flagged", polres["flagged"])
                pol.set_tag("policy.reason", polres["reason"])
                if polres["flagged"]:
                    raise HTTPException(status_code=400, detail="Message violates policy or contains PII.")

            # --- retrieval (RAG or FAQ lookup) ---
            with tracer.trace("citizen.retrieval.query") as ret:
                ret.set_tag("source", "federal_faq_index")
                docs = retrieve_docs(user_msg)
                ret.set_metric("retrieved_docs", len(docs))
                if docs:
                    ret.set_tag("docs.ids", ",".join(docs[:5]))

            # --- LLM call (OpenAI) ---
            with tracer.trace("citizen.llm.completion") as llm_span:
                # --- take advantage of Hallucination detection  ---
                llm_span.set_tag("model.name", OPENAI_MODEL)
                llm_span.set_metric("prompt.length", len(user_msg))
                start = time.time()
                
                try:

                    completion = openai_client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_msg},
                        ],
                        temperature=req.temperature or 0.2,
                        max_tokens=req.max_tokens or 300,
                    )
                    latency_s = time.time() - start
                    text = completion.choices[0].message.content if completion and completion.choices else ""
                    llm_span.set_metric("ml.latency_s", round(latency_s, 4))
                    if hasattr(completion, "usage") and completion.usage:
                        # OpenAI Python v1 returns usage on responses; guard just in case
                        llm_span.set_metric("tokens.prompt", getattr(completion.usage, "prompt_tokens", 0) or 0)
                        llm_span.set_metric("tokens.completion", getattr(completion.usage, "completion_tokens", 0) or 0)
                        llm_span.set_metric("tokens.total", getattr(completion.usage, "total_tokens", 0) or 0)
                except Exception as e:
                    llm_span.set_tag("error", True)
                    llm_span.set_tag("error.msg", str(e))
                    raise HTTPException(status_code=500, detail=f"LLM error: {e}")

            # --- response assembly (post-process + light safety) ---
            with tracer.trace("citizen.response.assembly") as asm:
                # basic blend of model result + any retrieved items
                if contains_pii(text):
                    text = ("I can’t share or process personal identifiers. "
                            "Please use official portals for sensitive data and avoid entering PII here.")
                if docs:
                    text = f"{text}\n\nReferences (suggested): " + ", ".join(docs)
                asm.set_metric("reply.length", len(text))
                asm.set_tag("reply.preview", text[:200])

            # annotate root with final preview for quick triage
            root.set_tag("ml.output_preview", text[:200])

            # Optional: if your ddtrace/LLMObs version supports explicit recording, you could send it here.
            # LLMObs may auto-ingest spans; keeping this explicit call commented avoids version coupling.
            # LLMObs.record_interaction(input=user_msg, output=text, metadata={"topic": topic})

            return {"response": text}

