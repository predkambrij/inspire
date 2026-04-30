import os, re, time, random
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_FILE = os.path.join(BASE_DIR, "seed.dat")
SEED2_FILE = os.path.join(BASE_DIR, "seed2.dat")
QUOTES_FILE = os.path.join(BASE_DIR, "quotes.dat")
QUOTES2_FILE = os.path.join(BASE_DIR, "quotes2.dat")
QUOTES3_FILE = os.path.join(BASE_DIR, "quotes3.dat")
API_URL = os.environ.get("API_URL", "https://api.z.ai/api/coding/paas/v4/chat/completions")
API_KEY = os.environ["API_KEY"]
MODEL = os.environ.get("MODEL", "glm-4.7")
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


def post_with_retry(prompt, retries=5):
    headers = {"Content-Type": "application/json", "Accept-Language": "en-US,en",
               "Authorization": f"Bearer {API_KEY}"}
    payload = {"model": MODEL, "messages": [
        {"role": "system", "content": "You are a creative writer who generates original inspirational quotes."},
        {"role": "user", "content": prompt}]}
    for attempt in range(retries):
        response = requests.post(API_URL, headers=headers, json=payload, timeout=300)
        if response.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        return response
    response.raise_for_status()


def parse_llm_response(response):
    lines = response.json()["choices"][0]["message"]["content"].strip().splitlines()
    results = []
    for line in lines:
        # Strip numbered/bullet prefixes (e.g. "1. ", "- ", "• ") and surrounding quotes
        line = re.sub(r"^\d+[.\)]\s*|^[-•]\s*", "", line).strip().strip("\"'")
        if line:
            results.append(f"|| {line}")
    return results


def call_llm(n, context_lines, topic):
    random.shuffle(context_lines)
    context = "\n".join(f"- {quote_text(q)}" for q in context_lines)
    prompt = (
        f"Generate {n} unique inspiring quotes about {topic}, one per line, with no extra text."
        f"Example quotes:\n{context}")
    return parse_llm_response(post_with_retry(prompt))


def do_generate(n, topic, mode):
    if mode == 1:
        # Context: last MAX_QUOTES from seeds + quotes.dat combined
        existing = read_lines(QUOTES_FILE)
        context = (read_seed() + existing)[-MAX_QUOTES:]
        new_quotes = call_llm(n, context, topic)
        write_lines(QUOTES_FILE, existing + new_quotes)
    elif mode == 2:
        # Context: seeds pinned at top + most recent generated quotes up to MAX_QUOTES total
        seed = read_seed()
        existing = read_lines(QUOTES2_FILE)
        context = seed + existing[-(MAX_QUOTES - len(seed)):]
        new_quotes = call_llm(n, context, topic)
        write_lines(QUOTES2_FILE, existing + new_quotes)
    else:
        # Context: seeds only, never influenced by previously generated quotes
        existing = read_lines(QUOTES3_FILE)
        new_quotes = call_llm(n, read_seed(), topic)
        write_lines(QUOTES3_FILE, existing + new_quotes)
    return new_quotes


def parse_body():
    # silent=True returns None instead of raising 400 on missing/malformed body
    body = request.get_json(force=True, silent=True) or {}
    return body.get("n", 5), body.get("topic", "discipline, life, motivation, and success"), body.get("mode", 1)


def quotes_file(mode):
    files = {1: QUOTES_FILE, 2: QUOTES2_FILE, 3: QUOTES3_FILE}
    return files[mode]


@app.route("/generate", methods=["POST"])
def generate():
    n, topic, mode = parse_body()
    try:
        do_generate(n, topic, mode=mode)
        return jsonify({"status": "ok", "generated": n, "total_quotes": len(read_lines(quotes_file(mode)))})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/generate-and-return", methods=["POST"])
def generate_and_return():
    n, topic, mode = parse_body()
    try:
        new = do_generate(n, topic, mode=mode)
        return jsonify({"status": "ok", "quotes": [format_quote(q) for q in new], "total_quotes": len(read_lines(quotes_file(mode)))})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/quotes", methods=["GET"])
def get_quotes():
    n = request.args.get("n", 5, type=int)
    mode = request.args.get("mode", 1, type=int)
    quotes = read_lines(quotes_file(mode))
    last = quotes[-n:]
    return jsonify({"quotes": [format_quote(q) for q in last], "count": len(last)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
