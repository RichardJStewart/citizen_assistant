import os
from ddtrace.llmobs import LLMObs

LLMObs.enable(
    site="datadoghq.com",  # Use "datadoghq.eu" if you’re on the EU site
    api_key=os.getenv("DD_API_KEY"),
    app_key=os.getenv("DD_APP_KEY"),
    project_name="Rick Project",
)

# 1. Create Dataset
dataset = LLMObs.create_dataset(
    dataset_name="demo_capitals",
    description="A dataset for testing knowledge of capital cities",
    records=[
        {"input_data": "What is the capital of France?", "expected_output": "Paris"},
        {"input_data": "What is the capital of Switzerland?", "expected_output": "Bern"}
    ])

# 2. Define Task and Evaluator(s)
def my_agent(input_data, config):
    output = "Paris"  # Replace with actual LLM or logic
    return output

def exact_match(input_data, output_data, expected_output):
    return output_data == expected_output

# 3. Create and Run Experiment
experiment = LLMObs.experiment(
    name="demo_capitals_experiment",
    task=my_agent,
    dataset=dataset,
    evaluators=[exact_match],
    description="Testing capital cities knowledge",
    config={"model_name": "hardcoded"}
)

results = experiment.run()

print("Experiment complete. View results here:")
print(experiment.url)

