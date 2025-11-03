# 🧠 Datadog LLM Observability Demo  
### *Citizen Services Virtual Assistant – SE Competition Edition*

## 🚀 Purpose
Demonstrate **Datadog LLM Observability** by monitoring, evaluating, and improving a GPT-4-powered federal **Citizen Services Virtual Assistant** that answers benefit eligibility questions.

The demo showcases:
- ✅ Environment validation (ddtrace + LLMObs)
- ✅ Dataset creation from citizen Q&A prompts
- ✅ Experiment execution with OpenAI
- ✅ Custom evaluators for accuracy, compliance, and latency
- ✅ Datadog tagging and trace correlation

---

## ⚙️ Setup

### **Install requirements**
```bash
pip install ddtrace openai pandas packaging

### **Set Environment Variables**
export DD_API_KEY="<your_datadog_api_key>"
export DD_APP_KEY="<your_datadog_app_key>"
export DD_SITE="datadoghq.com"       # or datadoghq.eu
export OPENAI_API_KEY="<your_openai_api_key>"
export OPENAI_MODEL="gpt-4o-mini"
export DATASET_CSV="Citizen_Eligibility_Demo_Dataset_with_Metadata.csv"  # optional

### **▶️ Run the Demo**
python3 citizen_assistant_experiment.py

### **Example Output**
✅ Detected ddtrace version: 2.8.4
✅ LLMObs module is available.
Experiment complete. View results here:
https://app.datadoghq.com/llm-observability/projects/Rick-Project/experiments/citizen_assistant_openai_v1


🧩 Experiment Components
Component	Description
Environment Check	Confirms compatible ddtrace + LLMObs install
Dataset	Eligibility prompts & expected outputs
Agent	GPT-4o-mini responding to citizen inquiries
Evaluators	exact_match_ci, policy_reference_present, pii_guard, latency_under_2s
Tags	service=citizen-assistant, env=demo, version=v1.3, ddtrace.version, model_provider=openai
📊 View in Datadog

The printed URL opens your Experiment Dashboard, where you can:

Inspect prompt → response → evaluation traces

Filter by service, env, version, or ddtrace.version

Compare experiments (e.g., model version or temperature change)

🧾 Notes

Uses synthetic, non-PII data for demo safety

Recommended ddtrace version: ≥ 2.8.0

Recommended max_tokens: 300 for GPT-4o-mini

Project tags: "source": "llm-observability", "ml_app": "citizen-assistant-chat"

