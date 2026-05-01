#!/bin/bash

scriptDir="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
outFile="$scriptDir/outfile.txt"

PROVIDERS='[
  "moonshotai/kimi-k2.6",
  "zai-glm-5",
  "deepseek/deepseek-v4-pro",
  "minimax/minimax-m2.7",
  "openai/gpt-5.5",
  "anthropic/claude-opus-4.6",
  "anthropic/claude-opus-4.7",
  "google/gemini-3.1-pro-preview",
  "x-ai/grok-4.3"
]'

curl -sX POST http://localhost:5050/generate-and-return-multiple -d "{\"providers\":${PROVIDERS},\"n\":5,\"mode\":3}" \
    | jq -r 'to_entries[] | "provider \(.key + 1) (\(.value.provider_model)):\n" + (.value.quotes | map("- " + .quote) | join("\n")) + "\n"' > "$outFile"
