# version 2 fix
from fastapi import FastAPI
import re

app = FastAPI()

def solve_math(query: str):
    # Handle addition like "What is 10 + 15?"
    match = re.search(r'(\d+)\s*\+\s*(\d+)', query)
    if match:
        a, b = map(int, match.groups())
        return f"The sum is {a + b}."
    
    return None


@app.post("/v1/answer")
async def answer(data: dict):
    query = data.get("query", "")

    result = solve_math(query)

    if result:
        return {"output": result}

    # fallback (important so API never breaks)
    return {"output": "Unable to process the query."}