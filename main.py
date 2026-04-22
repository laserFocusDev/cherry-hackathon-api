from fastapi import FastAPI
import re

app = FastAPI()

def solve_math(query: str):
    match = re.search(r'(\d+)\s*\+\s*(\d+)', query.lower())
    if match:
        a, b = map(int, match.groups())
        return f"The sum is {a + b}."
    return None


@app.post("/v1/answer")
async def answer(data: dict):
    query = data.get("query", "")
    assets = data.get("assets", [])  # <-- NEW (important)

    result = solve_math(query)

    if result:
        return {"output": result}

    return {"output": "Unable to process the query."}