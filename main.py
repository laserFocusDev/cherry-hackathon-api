import re
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    assets: Optional[Any] = None


def clean(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(round(value, 6))


# 🔥 Convert assets → string safely
def assets_to_text(assets: Any) -> str:
    if assets is None:
        return ""

    if isinstance(assets, str):
        return assets

    if isinstance(assets, list):
        return " ".join(str(x) for x in assets)

    if isinstance(assets, dict):
        return " ".join(str(v) for v in assets.values())

    return str(assets)


def solve_query(query: str, assets: Any) -> str:
    # 🔥 Merge query + assets
    combined = query + " " + assets_to_text(assets)
    q = combined.lower()

    # 🔥 Clean noise
    q = re.sub(r'[^\d+\-*/.\s]', ' ', q)

    # 🔥 Normalize operators
    q = re.sub(r'\bdivided\s+by\b', '/', q)
    q = re.sub(r'\bmultiplied\s+by\b', '*', q)
    q = re.sub(r'\btimes\b', '*', q)
    q = re.sub(r'\bplus\b', '+', q)
    q = re.sub(r'\bminus\b', '-', q)
    q = re.sub(r'\bsubtract\b', '-', q)
    q = re.sub(r'\badd\b', '+', q)
    q = re.sub(r'\bover\b', '/', q)
    q = re.sub(r'\btotal\b', '+', q)

    # 🔥 Extract expression
    match = re.search(r'(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)', q)

    if match:
        a = float(match.group(1))
        op = match.group(2)
        b = float(match.group(3))

        try:
            if op == '+':
                return f"The sum is {clean(a + b)}."
            elif op == '-':
                return f"The difference is {clean(a - b)}."
            elif op == '*':
                return f"The product is {clean(a * b)}."
            elif op == '/':
                if b == 0:
                    return "Unable to process."
                return f"The quotient is {clean(a / b)}."
        except:
            return "Unable to process."

    # 🔥 FALLBACK using ALL numbers (query + assets)
    nums = re.findall(r'\d+', q)

    if len(nums) >= 2:
        a, b = int(nums[0]), int(nums[1])
        return f"The sum is {a + b}."

    return "Unable to process."


@app.post("/v1/answer")
async def answer(req: QueryRequest):
    try:
        return {"output": solve_query(req.query, req.assets)}
    except:
        return {"output": "Unable to process."}


@app.get("/")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
