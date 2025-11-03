import pandas as pd
import yaml

# --- METADATA BLOCK ---
metadata = {
    "dataset_name": "citizen_eligibility_demo",
    "description": (
        "Synthetic dataset simulating citizen interactions with a virtual assistant "
        "for federal benefit eligibility and program inquiries. Demonstrates Datadog "
        "LLM Observability dataset creation, evaluation, and experiment comparison."
    ),
    "project_metadata": {
        "project_owner": "Rick Stewart",
        "organization": "Datadog Federal Demo",
        "region": "US",
        "created_at": "2025-11-02",
        "version": "1.0",
        "tags": ["LLM Observability", "Citizen Services", "Demo", "Compliance"],
    },
    "columns": [
        {"name": "input_data", "description": "Citizen's natural-language question"},
        {"name": "expected_output", "description": "Ideal or policy-correct model response"},
        {"name": "category", "description": "Thematic grouping for the request"},
        {"name": "intent", "description": "User intent behind query"},
        {"name": "complexity_level", "description": "Difficulty level of the query"},
        {"name": "source_channel", "description": "Channel of origin (chatbot, portal, etc.)"},
        {"name": "context_id", "description": "Unique ID for conversation/session"},
        {"name": "region", "description": "Geographic scope"},
        {"name": "confidence_threshold", "description": "Target evaluator pass threshold"},
        {"name": "evaluation_type", "description": "Evaluator(s) applied"},
        {"name": "policy_reference", "description": "Relevant policy or agency source"},
        {"name": "last_updated", "description": "Last policy verification date"},
    ],
}

# --- Load your dataset ---
df = pd.read_csv("Citizen_Eligibility_Demo_Dataset.csv")

# Add metadata columns
df["intent"] = "Eligibility Inquiry"
df["complexity_level"] = "basic"
df["source_channel"] = "Citizen Chatbot"
df["context_id"] = [f"citizen_eligibility_demo_{i+1:03d}" for i in range(len(df))]
df["region"] = "Federal"
df["confidence_threshold"] = 0.9
df["policy_reference"] = "General Federal Benefits Guidance"
df["last_updated"] = "2025-11-02"

# --- Write combined file ---
metadata_yaml = yaml.dump(metadata, sort_keys=False)

with open("Citizen_Eligibility_Demo_Dataset_with_Metadata.csv", "w") as f:
    f.write("# --- METADATA ---\n")
    f.write(metadata_yaml)
    f.write("# --- DATA ---\n")
    df.to_csv(f, index=False)

print("✅ Created Citizen_Eligibility_Demo_Dataset_with_Metadata.csv")

