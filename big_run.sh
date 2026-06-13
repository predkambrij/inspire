#!/bin/bash

scriptDir="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
outFile="$scriptDir/outfile.txt"

PROVIDERS='[
  "moonshotai/kimi-k2.6",
  "minimax/minimax-m2.7",
  "x-ai/grok-4.3",
  "deepseek/deepseek-v4-pro",
  "zai-glm-5",
  "anthropic/claude-opus-4.8",
  "google/gemini-3.1-pro-preview",
  "google/gemini-3.5-flash",
  "openai/gpt-5.5"
]'

# Choose 2 random providers from the list
PROVIDERS=$(echo "$PROVIDERS" | jq -r '.[]' | shuf -n 2 | jq -R . | jq -s .)

# Backup existing outFile before overriding
if [ -f "$outFile" ]; then
    cp "$outFile" "${outFile%.txt}_$(date +%Y%m%d_%H%M%S).txt"
fi

curl -sX POST http://localhost:5050/generate-and-return-multiple -d "{\"providers\":${PROVIDERS},\"n\":5,\"topics\":\"unspecified\",\"mode\":3}" \
    | jq -r 'to_entries[] | "provider \(.key + 1) (\(.value.provider_model)):\n" + (.value.quotes | map("- " + .quote) | join("\n")) + "\n"' > "$outFile"
