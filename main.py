import re
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Any, Optional

app = FastAPI(title="Benchmarking API", version="3.0.0")

# ─────────────────────────────────────────────
# Schema  (query optional → empty string default, never 422)
# ─────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: Optional[str] = ""
    assets: Optional[Any] = None


# ─────────────────────────────────────────────
# Global: catch ALL validation errors → friendly response
# ─────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return _respond("Unable to process the query.")

@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    return _respond("Unable to process the query.")


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
OP_LABELS: dict[str, str] = {
    "+": "sum",
    "-": "difference",
    "*": "product",
    "/": "quotient",
}

NUM = r"-?\d+(?:\.\d+)?"   # digit number sub-pattern

# Word → digit map (order matters: longest first for replacement)
WORD_NUM_MAP = {
    "nineteen": 19, "eighteen": 18, "seventeen": 17, "sixteen": 16,
    "fifteen": 15, "fourteen": 14, "thirteen": 13, "twelve": 12,
    "eleven": 11, "hundred": 100, "thousand": 1000,
    "ninety": 90, "eighty": 80, "seventy": 70, "sixty": 60,
    "fifty": 50, "forty": 40, "thirty": 30, "twenty": 20,
    "twenty-": 20,   # handle hyphenated like "twenty-five"
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


# ─────────────────────────────────────────────
# Word-number resolver
# ─────────────────────────────────────────────
def replace_word_numbers(text: str) -> str:
    """
    Replace written numbers with digits.
    Handles: 'fifteen', 'twenty five', 'twenty-five', 'one hundred'
    """
    # Only replace hyphens between letters (e.g. "twenty-five" → "twenty five")
    # Do NOT replace arithmetic minus signs like '20 - 8' or '-5'
    text = re.sub(r'([a-z])-([a-z])', r'\1 \2', text)

    # Compound tens+ones: "twenty five" → 25
    tens_words = ["twenty", "thirty", "forty", "fifty",
                  "sixty", "seventy", "eighty", "ninety"]
    ones_words = ["one", "two", "three", "four", "five",
                  "six", "seven", "eight", "nine"]

    for tens in tens_words:
        for ones in ones_words:
            compound = tens + " " + ones
            if compound in text:
                value = WORD_NUM_MAP[tens] + WORD_NUM_MAP[ones]
                text = text.replace(compound, str(value))

    # "one hundred" → 100, "two hundred" → 200, etc.
    for ones in ones_words + ["ten", "eleven", "twelve", "thirteen",
                               "fourteen", "fifteen", "sixteen",
                               "seventeen", "eighteen", "nineteen"]:
        pattern = ones + " hundred"
        if pattern in text and ones in WORD_NUM_MAP:
            text = text.replace(pattern, str(WORD_NUM_MAP[ones] * 100))

    # Single word numbers (longest match first to avoid partial replacements)
    for word, num in sorted(WORD_NUM_MAP.items(), key=lambda x: -len(x[0])):
        text = re.sub(r"\b" + re.escape(word) + r"\b", str(num), text)

    return text


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _clean(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(round(value, 10))


def _compute(a: float, op: str, b: float):
    try:
        if op == "+":   result = a + b
        elif op == "-": result = a - b
        elif op == "*": result = a * b
        elif op == "/":
            if b == 0: return None
            result = a / b
        else: return None
        return OP_LABELS[op], result
    except Exception:
        return None


# ─────────────────────────────────────────────
# Multi-pattern math extractor
# ─────────────────────────────────────────────
def extract_and_solve(query: str):
    if not query or not query.strip():
        return None

    # Step 1: lowercase + replace word numbers
    raw = query.lower().strip()
    raw = replace_word_numbers(raw)

    # ── P1: Noun form "op of X and Y" ───────────────────────────────────────
    OF_OPS = [
        (r"(?:sum|total|addition)\s+of\s+(" + NUM + r")\s+and\s+(" + NUM + r")", "+"),
        (r"(?:difference|subtraction)\s+of\s+(" + NUM + r")\s+and\s+(" + NUM + r")", "-"),
        (r"(?:product|multiplication)\s+of\s+(" + NUM + r")\s+and\s+(" + NUM + r")", "*"),
        (r"(?:quotient|division)\s+of\s+(" + NUM + r")\s+(?:and|by)\s+(" + NUM + r")", "/"),
    ]
    for pat, op in OF_OPS:
        m = re.search(pat, raw)
        if m:
            return _compute(float(m.group(1)), op, float(m.group(2)))

    # ── P2: Imperative verb forms ────────────────────────────────────────────
    m = re.search(r"\badd(?:ed)?\s+(" + NUM + r")\s+(?:and|to)\s+(" + NUM + r")", raw)
    if m:
        return _compute(float(m.group(1)), "+", float(m.group(2)))

    m = re.search(r"\bsubtract(?:ed)?\s+(" + NUM + r")\s+from\s+(" + NUM + r")", raw)
    if m:
        return _compute(float(m.group(2)), "-", float(m.group(1)))  # reversed!

    m = re.search(r"\bmultiply(?:ied)?\s+(" + NUM + r")\s+(?:by|and|with)\s+(" + NUM + r")", raw)
    if m:
        return _compute(float(m.group(1)), "*", float(m.group(2)))

    m = re.search(r"\bdivide[d]?\s+(" + NUM + r")\s+by\s+(" + NUM + r")", raw)
    if m:
        return _compute(float(m.group(1)), "/", float(m.group(2)))

    # ── P3: "X divided/multiplied by Y" ─────────────────────────────────────
    m = re.search(r"(" + NUM + r")\s+divided\s+by\s+(" + NUM + r")", raw)
    if m:
        return _compute(float(m.group(1)), "/", float(m.group(2)))

    m = re.search(r"(" + NUM + r")\s+multiplied\s+by\s+(" + NUM + r")", raw)
    if m:
        return _compute(float(m.group(1)), "*", float(m.group(2)))

    # ── P4: Word-operator substitution → symbolic ────────────────────────────
    text = raw
    text = re.sub(r"\bdivided\s+by\b",    "/", text)
    text = re.sub(r"\bmultiplied\s+by\b", "*", text)
    text = re.sub(r"\btimes\b",           "*", text)
    text = re.sub(r"\bplus\b",            "+", text)
    text = re.sub(r"\bminus\b",           "-", text)
    text = re.sub(r"\bsubtracted\s+from\b", "-", text)
    text = re.sub(r"\bover\b",            "/", text)

    # ── P5: Pure symbolic expression ─────────────────────────────────────────
    SYMBOLIC = r"(" + NUM + r")\s*([+\-*/])\s*(" + NUM + r")"
    m = re.search(SYMBOLIC, text)
    if m:
        return _compute(float(m.group(1)), m.group(2), float(m.group(3)))

    return None


# ─────────────────────────────────────────────
# Shared response builder
# ─────────────────────────────────────────────
def _respond(output: str) -> JSONResponse:
    return JSONResponse(
        content={"output": output},
        headers={"ngrok-skip-browser-warning": "true"},
    )


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────
@app.post("/v1/answer")
async def answer(request: QueryRequest) -> JSONResponse:
    try:
        result = extract_and_solve(request.query or "")
        if result is None:
            return _respond("Unable to process the query.")
        label, value = result
        return _respond(f"The {label} is {_clean(value)}.")
    except Exception:
        return _respond("Unable to process the query.")


@app.get("/")
async def health() -> JSONResponse:
    return _respond("Benchmarking API is live.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
