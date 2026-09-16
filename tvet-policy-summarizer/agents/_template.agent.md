---
name: {{AGENT_NAME}}
description: Describe what this agent does in one sentence
# task selects the harness pipeline: policy_summary | summary_review
task: policy_summary
# backend: ollama | openai_compatible | mock
backend: ollama
model: {{DEFAULT_MODEL}}
temperature: 0.1
max_words: 80
max_retries: 3
chunk_chars: 6000
max_chunks: 20
output_suffix: .summary.md
map_prompt: prompts/map-step.md
reduce_prompt: prompts/reduce-step.md
include: [prompts/style-guide.md]
---
Write the system prompt for this agent here.
Files listed in "include" are appended to this prompt.
