# Inspire

LLM-powered infinite inspirational quote generator. Generates unique quotes via API, stores them in flat files, and serves them over REST. This app was built with AI-assisted software

## Setup

```bash
touch quotes.dat quotes2.dat quotes3.dat
cp .env.sample .env # and configure API key
docker compose up -d
```

## Modes

| Mode | File | Context used for generation |
|------|------|-----------------------------|
| 1 | `quotes.dat` | seeds + quotes.dat, use last `MAX_QUOTES` |
| 2 | `quotes2.dat` | seeds pinned + most recent generated up to `MAX_QUOTES` combined|
| 3 | `quotes3.dat` | seeds only (`seed.dat` + `seed2.dat`) |

## API

All endpoints accept an optional JSON body with `n` (count, default 5), `topic` (default "discipline, life, motivation, and success"), and `mode` (1/2/3, default 1).

```bash
# Generate and save quotes
curl -X POST http://localhost:5050/generate
curl -X POST http://localhost:5050/generate -d '{"n":5,"topic":"courage","mode":2}'
curl -X POST http://localhost:5050/generate -d '{"n":5,"topic":"courage","mode":3}'

# Generate and return quotes
curl -X POST http://localhost:5050/generate-and-return
curl -X POST http://localhost:5050/generate-and-return -d '{"n":5,"topic":"resilience","mode":2}'
curl -X POST http://localhost:5050/generate-and-return -d '{"n":5,"topic":"resilience","mode":3}'

# Get last N saved quotes
curl "http://localhost:5050/quotes"
curl "http://localhost:5050/quotes?n=5&mode=2"
curl "http://localhost:5050/quotes?n=5&mode=3"
```

## File format

Quotes use `author || quote` format. LLM-generated quotes have no author. Authors are stripped from context when prompting the LLM.

```
Steve Jobs || The only way to do great work is to love what you do.
|| Dream big and dare to fail.
```
