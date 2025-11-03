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
````

### **Set Environment Variables**
export DD_API_KEY="<your_datadog_api_key>"
export DD_APP_KEY="<your_datadog_app_key>"
export DD_SITE="datadoghq.com"       # or datadoghq.eu
export OPENAI_API_KEY="<your_openai_api_key>"
export OPENAI_MODEL="gpt-4o-mini"
export DATASET_CSV="Citizen_Eligibility_Demo_Dataset_with_Metadata.csv"  # optional


### **▶️ Run the Demo**
```bash
python3 citizen_assistant_experiment.py
````

### **Example Output**
✅ Detected ddtrace version: 2.8.4
✅ LLMObs module is available.
Experiment complete. View results here:
https://app.datadoghq.com/llm-observability/projects/Rick-Project/experiments/citizen_assistant_openai_v1


### **🧩 Experiment Components**
- Environment Check	Confirms compatible ddtrace + LLMObs install
- Dataset	Eligibility prompts & expected outputs
- Agent	GPT-4o-mini responding to citizen inquiries
- Evaluators	exact_match_ci, policy_reference_present, pii_guard, latency_under_2s
- Tags	service=citizen-assistant, env=demo, version=v1.3, ddtrace.version, model_provider=openai

### **📊 View in Datadog**

The printed URL opens your Experiment Dashboard, where you can:

- Inspect prompt → response → evaluation traces

- Filter by service, env, version, or ddtrace.version

- Compare experiments (e.g., model version or temperature change)

### **🧾 Notes**

- Uses synthetic, non-PII data for demo safety
- Recommended ddtrace version: ≥ 2.8.0
- Recommended max_tokens: 300 for GPT-4o-mini
- Project tags: "source": "llm-observability", "ml_app": "citizen-assistant-chat"

---

## 🐍 Python Installation & Environment Setup

These demo scripts require **Python 3.9 or newer** (recommended: **Python 3.11+**).  
Follow the steps below to install Python and configure your environment on macOS or Linux.

### 1️⃣ Verify if Python is installed
```bash
python3 --version
````

You should see output like:

```
Python 3.11.6
```

If the command is not found or the version is below 3.9, proceed to install Python.

---

### 2️⃣ Install Python (macOS)

**Option A — via Homebrew (recommended):**

```bash
brew install python
```

**Option B — from python.org:**

1. Visit [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Download the latest **macOS installer**
3. Run it and ensure **“Add Python to PATH”** is selected

---

### 3️⃣ Verify installation

After installation, confirm it’s accessible:

```bash
python3 --version
pip3 --version
```

Both should return valid version numbers.

---

### 4️⃣ Create a virtual environment

It’s best practice to isolate dependencies for this demo:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

---

### 5️⃣ Upgrade pip and install dependencies

```bash
pip install --upgrade pip
pip install ddtrace openai pandas packaging
```

If you’re working with datasets that use YAML metadata:

```bash
pip install pyyaml
```

---

### 6️⃣ (Optional) Save dependencies for reproducibility

```bash
pip freeze > requirements.txt
```

You can later re-install them in one line:

```bash
pip install -r requirements.txt
```

---

### 7️⃣ Run your demo script

Once the environment is ready:

```bash
python3 citizen_assistant_experiment.py
```

If you see a message like:

```
✅ Detected ddtrace version: 2.8.4
✅ LLMObs module is available.
```

you’re good to go.

---

### 8️⃣ Deactivate the environment (when finished)

```bash
deactivate
```

---

### 🧠 Quick Reference

| Command                    | Purpose                      |
| -------------------------- | ---------------------------- |
| `python3 -m venv venv`     | Create isolated environment  |
| `source venv/bin/activate` | Activate environment         |
| `pip install ...`          | Install dependencies         |
| `deactivate`               | Exit environment             |
| `python3 scriptname.py`    | Run your Datadog demo script |

---

**💡 Tip:**
If you ever upgrade Python, recreate your `venv` — virtual environments are version-specific.

---

✅ Once complete, your environment is ready to run:

* `citizen_assistant_experiment.py`
* `add_metadata_block.py`
* Any other Datadog LLM Observability scripts



