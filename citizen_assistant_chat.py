import os
import re
import time
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# --- Datadog / ddtrace ---
from ddtrace import tracer, patch_all
from ddtrace.llmobs import LLMObs

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

def contains_pii(text: str) -> bool:
    if not text:
        return False
    for pat in PII_PATTERNS:
        if re.search(pat, text):
            return True
    return False


# ---------------------------
# 1) FastAPI app
# ---------------------------
app = FastAPI(title="Citizen Services Virtual Assistant")

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
                    url('https://images.unsplash.com/photo-1575311373936-4a39f57a4c87?auto=format&fit=crop&w=1600&q=80')
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
      <p class="subtitle">Ask benefit or eligibility questions securely — no personal data needed.</p>
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
def chat(req: ChatRequest, request: Request):
    user_msg = (req.message or "").strip()

    # Basic input validation & safety
    if not user_msg:
        raise HTTPException(status_code=400, detail="Empty message.")
    if contains_pii(user_msg):
        return JSONResponse(
            status_code=400,
            content={"error": "Your message appears to contain PII. Please remove sensitive information and try again."},
        )

    # Start a root span for the chat request (Datadog APM)
    with tracer.trace("chat.request", service="citizen-assistant", resource="/chat") as span:
        span.set_tag("app.user_agent", request.headers.get("user-agent", "unknown"))
        span.set_tag("ml.app", "citizen-assistant-chat")
        span.set_tag("ml.provider", "openai")
        span.set_tag("ml.model", OPENAI_MODEL)
        span.set_tag("ml.session_id", req.session_id or "anonymous")
        span.set_tag("ml.temperature", req.temperature)
        span.set_tag("ml.max_tokens", req.max_tokens)

        # LLM call span — captured as a child of chat.request
        start = time.time()
        try:
            # Optional: log input as an attribute for observability (avoid PII)
            span.set_tag("ml.prompt_preview", user_msg[:200])
            span.set_tag("ml.topic", detect_topic(user_msg))

            # --- OpenAI call ---
            completion = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
                temperature=req.temperature or 0.2,
                max_tokens=req.max_tokens or 300,
            )
            latency_s = time.time() - start
            text = completion.choices[0].message.content if completion and completion.choices else ""

            # Safety check on output
            if contains_pii(text):
                text = ("I can’t share or process personal identifiers. "
                        "Please use official portals for sensitive data and avoid entering PII here.")

            # Annotate span with result metadata
            span.set_tag("ml.latency_s", round(latency_s, 4))
            span.set_tag("ml.output_preview", text[:200])

            # (Optional) LLM Observability: send an interaction record.
            # Some versions of ddtrace.llmobs auto-ingest spans; this explicit block keeps the demo obvious.
            # If your version exposes helpers like LLMObs.record(...), you can wire them here.

            return {"response": text}

        except Exception as e:
            span.set_tag("error", True)
            span.set_tag("error.msg", str(e))
            raise HTTPException(status_code=500, detail=f"LLM error: {e}")

def detect_topic(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if "housing" in prompt_lower or "hud" in prompt_lower:
        return "Housing Assistance"
    elif "snap" in prompt_lower or "food" in prompt_lower:
        return "Food Assistance"
    elif "medicaid" in prompt_lower or "health" in prompt_lower:
        return "Healthcare Assistance"
    elif "veteran" in prompt_lower or "army" in prompt_lower or "navy" in prompt_lower:
        return "Veterans Benefits"
    elif "military" in prompt_lower:
        return "Veterans Benefits"
    else:
        return "General Inquiry"
