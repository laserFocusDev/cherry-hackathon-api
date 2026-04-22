from fastapi import FastAPI
import re

app = FastAPI()

def solve_math(q):
    match = re.search(r'(\d+)\s*\+\s*(\d+)', q)
    if match:
        a, b = map(int, match.groups())
        return f"The sum is {a+b}."
    return None

@app.post("/v1/answer")
async def answer(data: dict):
    query = data.get("query", "")

    result = solve_math(query)

    if result:
        return {"answer": result}

    return {"answer": "Cannot solve"}