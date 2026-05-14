# Inspire

LLM-powered infinite inspirational quote generator. Generates unique quotes via API, stores them in flat files, and serves them over REST. This app was built with AI-assisted software

## Setup

```bash
touch quotes.dat quotes2.dat quotes3.dat outfile.txt
cp config.py.sample config.py # and configure API keys
docker compose up -d --force-recreate --build
```

## Modes

| Mode | File | Context used for generation |
|------|------|-----------------------------|
| 1 | `quotes.dat` | seeds + quotes.dat, use last `MAX_QUOTES` |
| 2 | `quotes2.dat` | seeds pinned + most recent generated up to `MAX_QUOTES` combined|
| 3 | `quotes3.dat` | seeds only (`seed.dat` + `seed2.dat`) |

## API

All endpoints accept an optional JSON body with:
- `n`: count, default 5
- `topics`: default - themes defined in system prompt
- `mode` (1/2/3, default 1).

```bash
# Generate and save quotes
curl -X POST http://localhost:5050/generate
curl -X POST http://localhost:5050/generate -d '{"n":5,"topics":"courage","mode":2}'
curl -X POST http://localhost:5050/generate -d '{"provider_model":"zai-glm-5","n":5,"topics":"courage","mode":3}'

# Generate and return quotes
curl -X POST http://localhost:5050/generate-and-return
curl -X POST http://localhost:5050/generate-and-return -d '{"n":5,"topics":"resilience","mode":2}'
curl -X POST http://localhost:5050/generate-and-return -d '{"provider_model":"zai-glm-5","n":5,"topics":"resilience","mode":3}'

# Generate and return quotes for multiple provider calls
curl -sX POST http://localhost:5050/generate-and-return-multiple -d '{"providers":["zai-glm-5","zai-glm-5","google/gemini-3.1-pro-preview"],"n":5,"mode":3}' | jq -r 'to_entries[] | "provider \(.key + 1) (\(.value.provider_model)):\n" + (.value.quotes | map("- " + .quote) | join("\n")) + "\n"'

# Get last N saved quotes
curl "http://localhost:5050/quotes"
curl "http://localhost:5050/quotes?n=5&mode=2"
curl "http://localhost:5050/quotes?n=5&mode=3"

# Get the latest multiple-provider text output
curl "http://localhost:5050/quotes?mode=multiple"
```

## File format

Quotes use `author || quote` format. LLM-generated quotes have no author. Authors are stripped from context when prompting the LLM.

```
Steve Jobs || The only way to do great work is to love what you do.
|| Dream big and dare to fail.
```
