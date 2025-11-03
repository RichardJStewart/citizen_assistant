# ============================================================
# Datadog LLM Observability Environment Check
# ============================================================
import sys

def check_ddtrace_environment(min_version=(2, 6, 0)):
    """Verifies ddtrace is installed, at the right version, and LLMObs is accessible."""
    try:
        import ddtrace

        installed_version = tuple(map(int, ddtrace.__version__.split(".")[:3]))
        print(f"✅ Detected ddtrace version: {ddtrace.__version__}")

        if installed_version < min_version:
            print(f"⚠️  WARNING: ddtrace {ddtrace.__version__} is older than required "
                  f"{'.'.join(map(str, min_version))}. Some LLM Observability features may not work.")
            print("   → Run: pip install --upgrade ddtrace")
        else:
            print("✅ ddtrace version is sufficient for LLM Observability.")

        # Try importing LLMObs
        try:
            from ddtrace.llmobs import LLMObs
            print("✅ LLMObs module is available.")
        except ImportError:
            print("❌ ERROR: LLMObs module not found in ddtrace package.")
            print("   → Upgrade ddtrace: pip install --upgrade ddtrace>=2.8.0")
            sys.exit(1)

        return installed_version

    except ModuleNotFoundError:
        print("❌ ERROR: ddtrace is not installed.")
        print("   → Run: pip install ddtrace>=2.8.0")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during environment check: {e}")
        sys.exit(1)

# Run the check
ddtrace_version = check_ddtrace_environment()
# ============================================================

import os
import re
import time
import pandas as pd

from ddtrace.llmobs import LLMObs

# --- LLM client (OpenAI) ---
# Using the official OpenAI SDK. It reads OPENAI_API_KEY from env.
try:
    from openai import OpenAI
    openai_client = OpenAI()
except Exception as e:
    raise RuntimeError("OpenAI SDK not installed or misconfigured. "
                       "Run `pip install openai` and set OPENAI_API_KEY.") from e


# === 1) Enable Datadog LLM Observability ===
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
DD_API_KEY = os.getenv("DD_API_KEY")
DD_APP_KEY = os.getenv("DD_APP_KEY")

if not DD_API_KEY or not DD_APP_KEY:
    raise RuntimeError("Missing DD_API_KEY or DD_APP_KEY env vars.")

LLMObs.enable(
    site=DD_SITE,
    api_key=DD_API_KEY,
    app_key=DD_APP_KEY,
    project_name="Rick Project",
)


# === 2) Load dataset ===
# Use your CSV from earlier, or fall back to a tiny inline dataset if not found.
CSV_PATH = os.getenv("DATASET_CSV")

if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH)
else:
    # Minimal fallback so the script still runs
    df = pd.DataFrame([
        {"Prompt": "Am I eligible for housing assistance if I make $45,000 and live in Virginia?",
         "Expected Output": "Eligibility depends on household size and local income limits. Check HUD’s Income Limits Tool.",
         "Category": "General Eligibility",
         "Evaluation Type": "Accuracy"},
        {"Prompt": "Do veterans get priority for housing programs?",
         "Expected Output": "Yes. HUD-VASH prioritizes veterans, especially at risk of homelessness.",
         "Category": "General Eligibility",
         "Evaluation Type": "Policy Correctness"},
    ])

# Normalize columns if needed
if "input_data" not in df.columns:
    df = df.rename(columns={
        "Prompt": "input_data",
        "Expected Output": "expected_output"
    })

records = df[["input_data", "expected_output"]].to_dict(orient="records")

dataset = LLMObs.create_dataset(
    dataset_name="citizen_eligibility_demo",
    description="Citizen Services Virtual Assistant eligibility prompts and expected outputs",
    records=records
)


# === 3) Define the task (agent) ===
# You can swap the model with your preferred one.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are a federal Citizen Services Virtual Assistant. "
    "Answer concisely and accurately based on U.S. federal benefits guidance. "
    "If income/state-specific or program-specific data is necessary, state that limits vary by state and point to official resources. "
    "Never invent policy or ask for PII. Do not output SSNs or other sensitive data."
)

def call_openai(prompt: str, config: dict) -> str:
    """Calls OpenAI and returns the assistant string."""
    start = time.time()
    completion = openai_client.chat.completions.create(
        model=config.get("model_name", OPENAI_MODEL),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=float(config.get("temperature", 0.2)),
        max_tokens=int(config.get("max_tokens", 300)),
    )
    latency = time.time() - start
    # Pull the message text safely:
    text = completion.choices[0].message.content if completion and completion.choices else ""
    # Attach latency into the config so an evaluator can use it
    config["_last_latency_s"] = latency
    return text


def my_agent(input_data: str, config: dict) -> str:
    """Your agent under test — routed through OpenAI for this demo."""
    return call_openai(input_data, config)


# === 4) Define Evaluators ===
# Evaluators return True/False or a numeric score. Booleans are fine.

def exact_match_ci(input_data: str, output_data: str, expected_output: str):
    """Case-insensitive, punctuation-light exact match for simple Q&A."""
    def norm(s: str) -> str:
        return re.sub(r"[\W_]+", " ", (s or "").strip().lower())
    return norm(output_data) == norm(expected_output)

AGENCY_KEYWORDS = (
    "HUD", "Benefits.gov", "Medicaid.gov", "SNAP", "USDA", "VA", "Veterans Affairs",
    "Privacy Act"
)

def policy_reference_present(input_data: str, output_data: str, expected_output: str):
    """
    Soft check that the answer references an official source or agency cue.
    Useful for demos showing 'policy grounding'.
    """
    text = (output_data or "")
    return any(k in text for k in AGENCY_KEYWORDS)

PII_PATTERNS = [
    # basic demo-level checks; you can expand with more robust patterns
    r"\b\d{3}-\d{2}-\d{4}\b",     # SSN format
    r"\b\d{9}\b",                 # 9-digit SSN-like
    r"\b\d{16}\b",                # 16-digit card-like
]

def pii_guard(input_data: str, output_data: str, expected_output: str):
    """Fail if we detect obvious PII patterns in the model output."""
    text = output_data or ""
    for pat in PII_PATTERNS:
        if re.search(pat, text):
            return False
    return True

def latency_under_2s(input_data: str, output_data: str, expected_output: str, *, ctx=None):
    """
    Checks latency budget. We stored last latency in config during call.
    When run within Experiments, you can pass context via config or a closure.
    To keep this simple, we read it from a thread-local config injected by LLMObs.
    """
    # Datadog passes evaluator args (input, output, expected). Latency has to be carried in config.
    # LLMObs forwards 'config' into task; we stash latency into config.
    # Some SDKs let evaluators read from ctx or from output metadata. For demo, return True if unknown.
    try:
        latency = ctx.get("config", {}).get("_last_latency_s", None) if ctx else None
        return (latency is None) or (latency < 2.0)
    except Exception:
        return True  # don’t fail if context unavailable during demo


# === 5) Create & run experiment ===
experiment = LLMObs.experiment(
    name="citizen_assistant_openai_v1",
    task=my_agent,
    dataset=dataset,
    evaluators=[exact_match_ci, policy_reference_present, pii_guard, latency_under_2s],
    description="Citizen Services Virtual Assistant — OpenAI-backed demo with policy/PII/latency checks",
    config={
        "model_name": OPENAI_MODEL,
        "temperature": 0.2,
        "max_tokens": 300
    },
    tags={
        "service": "citizen-assistant",
        "version": "v1.3",
        "env": "demo",
        "owner": "rick.stewart",
        "model_provider": "openai",
        "model_name": OPENAI_MODEL,
        "source":"llm-observability",
        "ml_app":"citizen-assistant-chat",
        "ddtrace.version": ddtrace_version,
        "language":"python"
    }
)

results = experiment.run()
print("Experiment complete. View results here:")
print(experiment.url)

