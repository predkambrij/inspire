import os, re, time, random, json
import requests
from flask import Flask, request, jsonify
from config import DEFAULT_PROVIDER_MODEL, PROVIDER_MODELS, DEBUG_LOGGING
from config import SYSTEM_PROMPT, get_prompt

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_FILE = os.path.join(BASE_DIR, "seed.dat")
SEED2_FILE = os.path.join(BASE_DIR, "seed2.dat")
QUOTES_FILE = os.path.join(BASE_DIR, "quotes.dat")
QUOTES2_FILE = os.path.join(BASE_DIR, "quotes2.dat")
QUOTES3_FILE = os.path.join(BASE_DIR, "quotes3.dat")
OUTFILE_TXT = os.path.join(BASE_DIR, "outfile.txt")
MAX_QUOTES = 200


def read_lines(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath) as f:
        return [l.strip() for l in f if l.strip() and not l.strip().startswith("//")]

def read_seed():
    return read_lines(SEED_FILE) + read_lines(SEED2_FILE)

def write_lines(filepath, lines):
    content = "\n".join(lines) + "\n" if lines else ""
    with open(filepath, "w") as f:
        f.write(content)

def quote_text(line):
    if "||" in line:
        return line.split("||", 1)[1].strip()
    return line.strip()

def format_quote(line):
    if "||" in line:
        author, quote = line.split("||", 1)
        return {"author": author.strip() or None, "quote": quote.strip()}
    return {"author": None, "quote": line.strip()}

def apply_reasoning(payload, config):
    effort = config.get("effort")
    if not effort:
        return

    if effort == "reasoning-enabled":
        payload["reasoning"] = {"enabled": True}

    elif effort == "reasoning-low":
        payload["reasoning"] = {"enabled": True}
        payload["verbosity"] = "low"
    elif effort == "reasoning-medium":
        payload["reasoning"] = {"enabled": True}
        payload["verbosity"] = "medium"
    elif effort == "reasoning-high":
        payload["reasoning"] = {"enabled": True}
        payload["verbosity"] = "high"
    elif effort == "reasoning-xhigh":
        payload["reasoning"] = {"enabled": True}
        payload["verbosity"] = "xhigh"
    elif effort == "reasoning-max":
        payload["reasoning"] = {"enabled": True}
        payload["verbosity"] = "max"

    elif effort == "reasoning-disabled":
        payload["reasoning"] = {"enabled": False}

    elif effort == "thinking-disabled":
        payload["thinking"] = {"type": "disabled"}
    elif effort == "thinking-high":
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = "high"
    elif effort == "thinking-max":
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = "max"

    else: # openai-compatible
        payload["reasoning"] = {"effort": effort}

def post_with_retry(prompt, provider_model, retries=5):
    config = PROVIDER_MODELS[provider_model]
    headers = {"Content-Type": "application/json", "Accept-Language": "en-US,en",
               "Authorization": f"Bearer {config['api_key']}"}
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}]}

    if config.get("provider"):
        payload["provider"] = config["provider"]

    apply_reasoning(payload, config)

    for attempt in range(retries):
        if DEBUG_LOGGING:
            print(f"[DEBUG LLM REQUEST] URL: {config['api_url']}", flush=True)
            print(f"[DEBUG LLM REQUEST] Payload: {json.dumps(payload, indent=2)}", flush=True)
        response = requests.post(config["api_url"], headers=headers, json=payload, timeout=600)
        if DEBUG_LOGGING:
            print(f"[DEBUG LLM RESPONSE] Status: {response.status_code} Body: {json.dumps(response.json(), indent=2)}", flush=True)
        if response.status_code in [429, 500, 502]:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        return response
    response.raise_for_status()

def parse_llm_response(response, provider_model):
    lines = response.json()["choices"][0]["message"]["content"].strip().splitlines()
    results = []
    for line in lines:
        # Strip numbered/bullet prefixes (e.g. "1. ", "- ", "• ")
        line = re.sub(r"^\d+[.\)]\s*|^[-•]\s*", "", line).strip()
        if line:
            results.append(f"{provider_model} || {line}")
    return results

def call_llm(n, context_lines, topics, provider_model):
    random.shuffle(context_lines)
    context = "\n".join(f"- {quote_text(q)}" for q in context_lines)
    prompt = get_prompt(n, topics, context)
    return parse_llm_response(post_with_retry(prompt, provider_model), provider_model)

def do_generate(n, topics, mode, provider_model):
    if mode == 1:
        # Context: last MAX_QUOTES from seeds + quotes.dat combined
        existing = read_lines(QUOTES_FILE)
        context = (read_seed() + existing)[-MAX_QUOTES:]
        new_quotes = call_llm(n, context, topics, provider_model)
        write_lines(QUOTES_FILE, existing + new_quotes)
    elif mode == 2:
        # Context: seeds pinned at top + most recent generated quotes up to MAX_QUOTES total
        seed = read_seed()
        existing = read_lines(QUOTES2_FILE)
        context = seed + existing[-(MAX_QUOTES - len(seed)):]
        new_quotes = call_llm(n, context, topics, provider_model)
        write_lines(QUOTES2_FILE, existing + new_quotes)
    else:
        # Context: seeds only, never influenced by previously generated quotes
        existing = read_lines(QUOTES3_FILE)
        new_quotes = call_llm(n, read_seed(), topics, provider_model)
        write_lines(QUOTES3_FILE, existing + new_quotes)
    return new_quotes

def parse_body():
    # silent=True returns None instead of raising 400 on missing/malformed body
    body = request.get_json(force=True, silent=True) or {}
    return (
        body.get("n", 5),
        body.get("topics", "unspecified"),
        body.get("mode", 1),
        body.get("provider_model", DEFAULT_PROVIDER_MODEL),
        body.get("providers", []))

def quotes_file(mode):
    files = {1: QUOTES_FILE, 2: QUOTES2_FILE, 3: QUOTES3_FILE}
    return files[mode]

def generated_quote_response(n, topics, mode, provider_model):
    new = do_generate(n, topics, mode=mode, provider_model=provider_model)
    return {
        "status": "ok",
        "provider_model": provider_model,
        "quotes": [format_quote(q) for q in new],
        "total_quotes": len(read_lines(quotes_file(mode)))
    }


@app.route("/generate", methods=["POST"])
def generate():
    n, topics, mode, provider_model, _ = parse_body()
    try:
        do_generate(n, topics, mode=mode, provider_model=provider_model)
        return jsonify({"status": "ok", "generated": n, "provider_model": provider_model, "total_quotes": len(read_lines(quotes_file(mode)))})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/generate-and-return", methods=["POST"])
def generate_and_return():
    n, topics, mode, provider_model, _ = parse_body()
    try:
        return jsonify(generated_quote_response(n, topics, mode, provider_model))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/generate-and-return-multiple", methods=["POST"])
def generate_and_return_multiple():
    n, topics, mode, _, providers = parse_body()

    results = []
    for provider_model in providers:
        try:
            results.append(generated_quote_response(n, topics, mode, provider_model))
        except Exception as e:
            if DEBUG_LOGGING:
                print(f"[DEBUG SKIPPED PROVIDER] {provider_model}: {e}", flush=True)
    return jsonify(results)

@app.route("/quotes", methods=["GET"])
def get_quotes():
    n = request.args.get("n", 5, type=int)
    mode_arg = request.args.get("mode", "1")
    if mode_arg == "multiple":
        with open(OUTFILE_TXT) as f:
            return app.response_class(f.read(), mimetype="text/plain")
    quotes = read_lines(quotes_file(int(mode_arg)))
    last = quotes[-n:]
    return jsonify({"quotes": [format_quote(q) for q in last], "count": len(last)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
