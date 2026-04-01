# Inspire

LLM-powered infinite inspirational quote generator. Generates unique quotes via API, stores them in flat files, and serves them over REST.

> This app was built with AI-assisted software

## Setup

```bash
touch quotes.dat quotes2.dat
cp .env.sample .env # and configure API key
docker compose up -d
```

## API

### Mode 1 — Simple rotation (`quotes.dat`, keeps last 100)

```bash
# Generate 5 quotes (default), save only
curl -X POST http://localhost:5050/generate

# Generate 3 quotes on a topic, return them
curl -X POST http://localhost:5050/generate-and-return -H "Content-Type: application/json" -d '{"n":3,"topic":"courage"}'

# Get last 5 quotes
curl http://localhost:5050/quotes?n=5
```

### Mode 2 — Seed-pinned rotation (`quotes2.dat`, seed stays at top, generated rotate after)

```bash
# Generate 5 quotes, save only
curl -X POST http://localhost:5050/generate2

# Generate 3 quotes, return them
curl -X POST http://localhost:5050/generate2-and-return -H "Content-Type: application/json" -d '{"n":3}'

# Get last 10 quotes
curl http://localhost:5050/quotes2?n=10
```


## File format

Quotes use `author || quote` format. LLM-generated quotes have no author (`|| quote`). Authors are stripped when seeding the LLM to avoid repetition.

```
Steve Jobs || The only way to do great work is to love what you do.
|| Dream big and dare to fail.
```
