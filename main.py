import re
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any

app = FastAPI()

class QueryRequest(BaseModel):
    query: Optional[str] = ""
    assets: Optional[Any] = None


def clean(x):
    x = float(x)
    return str(int(x)) if x == int(x) else str(round(x, 6))


def get_numbers(query, assets):
    text = (query + " " + str(assets)).lower()
    return list(map(float, re.findall(r'-?\d+(?:\.\d+)?', text)))


def solve(query, assets):
    text = (query + " " + str(assets)).lower()
    nums = get_numbers(query, assets)

    if not nums:
        return "Unable to process."

    # subtract X from Y
    if "subtract" in text and "from" in text and len(nums) >= 2:
        return f"The result is {clean(nums[1] - nums[0])}."

    # division
    if any(x in text for x in ["divide", "divided", "/"]) and len(nums) >= 2:
        if nums[1] == 0:
            return "Unable to process."
        return f"The result is {clean(nums[0] / nums[1])}."

    # multiplication
    if any(x in text for x in ["multiply", "product", "*", "times"]) and len(nums) >= 2:
        result = 1
        for n in nums:
            result *= n
        return f"The result is {clean(result)}."

    # addition (default)
    if len(nums) >= 2:
        return f"The result is {clean(sum(nums))}."

    return "Unable to process."


@app.post("/v1/answer")
async def answer(req: QueryRequest):
    try:
        return {"output": solve(req.query or "", req.assets)}
    except:
        return {"output": "Unable to process."}


@app.get("/")
async def health():
    return {"status": "ok"}
