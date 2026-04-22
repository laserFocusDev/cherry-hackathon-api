import os
import re
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any
from groq import Groq

app = FastAPI()

# ──────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: Optional[str] = ""
    assets: Optional[Any] = None


# ──────────────────────────────────────────────
# LLM CLIENT
# ──────────────────────────────────────────────
_client = None

def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


SYSTEM_PROMPT = """You are a precise answer engine.

Rules:
- Answer directly.
- No explanation.
- No extra words.
- Arithmetic must be correct.
- Return only the final answer.
"""


# ──────────────────────────────────────────────
# UTIL
# ──────────────────────────────────────────────
def clean(x):
    try:
        x = float(x)
        return str(int(x)) if x == int(x) else str(round(x, 6))
    except:
        return x


def assets_to_text(assets):
    if not assets:
        return ""
    if isinstance(assets, list):
        return " ".join(map(str, assets))
    if isinstance(assets, dict):
        return " ".join(map(str, assets.values()))
    return str(assets)


# ──────────────────────────────────────────────
# OUTPUT NORMALIZER (CRITICAL)
# ──────────────────────────────────────────────
def normalize_output(text: str) -> str:
    nums = re.findall(r'-?\d+(?:\.\d+)?', text)

    if nums:
        return f"The result is {clean(nums[0])}."

    return "Unable to process."


# ──────────────────────────────────────────────
# RULE-BASED SOLVER (FAST PATH)
# ──────────────────────────────────────────────
def rule_solver(query, assets):
    combined = (query + " " + assets_to_text(assets)).lower()

    nums = list(map(int, re.findall(r'\d+', combined)))

    if not nums:
        return None

    # subtract X from Y
    if "subtract" in combined and "from" in combined and len(nums) >= 2:
        return f"The result is {nums[1] - nums[0]}."

    # division
    if any(x in combined for x in ["divide", "divided", "/"]) and len(nums) >= 2:
        if nums[1] == 0:
            return "Unable to process."
        return f"The result is {clean(nums[0] / nums[1])}."

    # multiplication
    if any(x in combined for x in ["multiply", "product", "*", "times"]) and len(nums) >= 2:
        result = 1
        for n in nums:
            result *= n
        return f"The result is {result}."

    # addition (fallback default)
    if len(nums) >= 2:
        return f"The result is {sum(nums)}."

    return None


# ──────────────────────────────────────────────
# LLM FALLBACK
# ──────────────────────────────────────────────
def llm_solver(query):
    try:
        client = get_client()

        response = client.chat.completions.create(
            model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
        )

        raw = response.choices[0].message.content.strip()
        return normalize_output(raw)

    except:
        return "Unable to process."


# ──────────────────────────────────────────────
# AGENT
# ──────────────────────────────────────────────
def agent(query, assets):
    if not query or len(query.strip()) < 2:
        return "Unable to process."

    # 1️⃣ rule-based first
    result = rule_solver(query, assets)
    if result:
        return result

    # 2️⃣ LLM fallback
    return llm_solver(query)


# ──────────────────────────────────────────────
# ENDPOINT
# ──────────────────────────────────────────────
@app.post("/v1/answer")
async def answer(req: QueryRequest):
    try:
        output = agent(req.query or "", req.assets)
        return {"output": output}
    except:
        return {"output": "Unable to process."}


@app.get("/")
async def health():
    return {"status": "ok"}


# ──────────────────────────────────────────────
# LOCAL RUN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)