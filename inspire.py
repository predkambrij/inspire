import os, re, time, requests
from flask import Flask, request, jsonify

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_FILE = os.path.join(BASE_DIR, "seed.dat")
QUOTES_FILE = os.path.join(BASE_DIR, "quotes.dat")
QUOTES2_FILE = os.path.join(BASE_DIR, "quotes2.dat")
API_URL = os.environ.get("API_URL", "https://api.z.ai/api/coding/paas/v4/chat/completions")
API_KEY = os.environ["API_KEY"]
MODEL = os.environ.get("MODEL", "glm-4.7")
MAX_QUOTES = 100


def read_lines(filepath):
    return [l.strip() for l in open(filepath) if l.strip()] if os.path.exists(filepath) else []


def write_lines(filepath, lines):
    open(filepath, "w").write("\n".join(lines) + "\n" if lines else "")


def quote_text(line):
    return line.split("||", 1)[1].strip() if "||" in line else line.strip()


def format_quote(line):
    if "||" in line:
        author, quote = line.split("||", 1)
        return {"author": author.strip() or None, "quote": quote.strip()}
    return {"author": None, "quote": line.strip()}


def call_llm(n, context_lines, topic):
    context = "\n".join(f"- {quote_text(q)}" for q in context_lines)
    prompt = (f"Generate exactly {n} unique, original inspirational quotes about {topic}. "
              f"One per line, no numbering, no bullets, no extra text. "
              f"Do NOT repeat these:\n{context}\n\nReturn ONLY the quotes, one per line.")
    headers = {"Content-Type": "application/json", "Accept-Language": "en-US,en",
               "Authorization": f"Bearer {API_KEY}"}
    payload = {"model": MODEL, "messages": [
        {"role": "system", "content": "You are a creative writer who generates original inspirational quotes."},
        {"role": "user", "content": prompt}]}
    for attempt in range(5):
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=300)
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        break
    else:
        resp.raise_for_status()
    results = []
    for line in resp.json()["choices"][0]["message"]["content"].strip().splitlines():
        cleaned = re.sub(r"^\d+[.\)]\s*", "", line).strip().strip('"\'')
        cleaned = re.sub(r"^[-•]\s*", "", cleaned).strip().strip('"\'')
        if cleaned:
            results.append(f"|| {cleaned}")
    return results


def do_generate(n, topic, mode):
    seed = read_lines(SEED_FILE)
    if mode == 1:
        existing = read_lines(QUOTES_FILE)
        context = (seed + existing)[-50:]
        new_quotes = call_llm(n, context, topic)
        write_lines(QUOTES_FILE, (existing + new_quotes)[-MAX_QUOTES:])
    else:
        if not read_lines(QUOTES2_FILE):
            write_lines(QUOTES2_FILE, seed)
        all_lines = read_lines(QUOTES2_FILE)
        seed_count = len(seed)
        generated = all_lines[seed_count:]
        max_gen_ctx = max(50 - seed_count, 0)
        context = seed + generated[-max_gen_ctx:]
        new_quotes = call_llm(n, context, topic)
        generated = (generated + new_quotes)[-(MAX_QUOTES - seed_count):]
        write_lines(QUOTES2_FILE, seed + generated)
    return new_quotes


def parse_body():
    body = request.get_json(force=True) if request.data else {}
    return body.get("n", 5), body.get("topic", "life, motivation, and success")


def quotes_file(mode):
    return QUOTES_FILE if mode == 1 else QUOTES2_FILE


# --- Mode 1: quotes.dat (simple rotate, last MAX kept) ---

@app.route("/generate", methods=["POST"])
def generate():
    n, topic = parse_body()
    try:
        do_generate(n, topic, mode=1)
        return jsonify({"status": "ok", "generated": n, "total_quotes": len(read_lines(QUOTES_FILE))})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/generate-and-return", methods=["POST"])
def generate_and_return():
    n, topic = parse_body()
    try:
        new = do_generate(n, topic, mode=1)
        return jsonify({"status": "ok", "quotes": [format_quote(q) for q in new], "total_quotes": len(read_lines(QUOTES_FILE))})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/quotes", methods=["GET"])
def get_quotes():
    n = request.args.get("n", 5, type=int)
    quotes = read_lines(QUOTES_FILE)
    last = quotes[-n:]
    return jsonify({"quotes": [format_quote(q) for q in last], "count": len(last)})


# --- Mode 2: quotes2.dat (seed pinned at top, generated rotate after) ---

@app.route("/generate2", methods=["POST"])
def generate2():
    n, topic = parse_body()
    try:
        do_generate(n, topic, mode=2)
        return jsonify({"status": "ok", "generated": n, "total_quotes": len(read_lines(QUOTES2_FILE))})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/generate2-and-return", methods=["POST"])
def generate2_and_return():
    n, topic = parse_body()
    try:
        new = do_generate(n, topic, mode=2)
        return jsonify({"status": "ok", "quotes": [format_quote(q) for q in new], "total_quotes": len(read_lines(QUOTES2_FILE))})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/quotes2", methods=["GET"])
def get_quotes2():
    n = request.args.get("n", 5, type=int)
    quotes = read_lines(QUOTES2_FILE)
    last = quotes[-n:]
    return jsonify({"quotes": [format_quote(q) for q in last], "count": len(last)})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
