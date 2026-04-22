from fastapi import FastAPI
import re

app = FastAPI()

# Precompile regex at module load time
_EXPR_RE = re.compile(r'(\d+(?:\.\d+)?(?:\s*[+\-*/]\s*\d+(?:\.\d+)?)+)')
_SPACE_RE = re.compile(r'\s+')

# Prebuilt safe eval environment (created once, reused every request)
_SAFE_ENV = {"__builtins__": {}}

# Operator to label map for O(1) lookup
_OP_MAP = {'+': "sum", '-': "difference", '*': "product", '/': "quotient"}


def solve_math(query: str) -> str | None:
    # Normalize unicode operators inline
    query = query.replace('\u2212', '-').replace('\u00d7', '*').replace('\u00f7', '/')

    m = _EXPR_RE.search(query)
    if not m:
        return None

    expr_clean = _SPACE_RE.sub('', m.group(1))

    try:
        result = eval(expr_clean, _SAFE_ENV, {})
    except Exception:
        return None

    if not isinstance(result, (int, float)):
        return None

    if isinstance(result, float):
        if result != result or result in (float('inf'), float('-inf')):
            return None
        result = int(result) if result.is_integer() else round(result, 10)

    # Detect operator from cleaned expr — first match wins
    op = next((_OP_MAP[c] for c in expr_clean if c in _OP_MAP), "result")

    return f"The {op} is {result}."


@app.post("/v1/answer")
async def answer(data: dict):
    result = solve_math(data.get("query", ""))
    return {"output": result if result else "Unable to process the query."}
