import pandas as pd

df = pd.read_csv("Citizen_Eligibility_Demo_Dataset.csv")
df["intent"] = "Eligibility Inquiry"
df["complexity_level"] = "basic"
df["source_channel"] = "Citizen Chatbot"
df["context_id"] = [f"citizen_eligibility_demo_{i+1:03d}" for i in range(len(df))]
df["region"] = "Federal"
df["confidence_threshold"] = 0.9
df["policy_reference"] = "General Federal Benefits Guidance"
df["last_updated"] = "2025-11-02"

df.to_csv("Citizen_Eligibility_Demo_Dataset_with_metadata.csv", index=False)
print("✅ Updated dataset saved: Citizen_Eligibility_Demo_Dataset_with_metadata.csv")

