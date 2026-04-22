from fastapi import FastAPI
import re

app = FastAPI()


def extract_expression(query: str):
    # Extract mathematical expression (numbers + operators)
    match = re.search(r'[\d\s\+\-\*\/\.]+', query)
    if match:
        return match.group().strip()
    return None


def safe_eval(expr: str):
    try:
        # Evaluate safely (only math)
        result = eval(expr)
        return result
    except:
        return None


def solve_math(query: str):
    expr = extract_expression(query)
    if not expr:
        return None

    result = safe_eval(expr)
    if result is None:
        return None

    # Format output cleanly
    if result == int(result):
        result = int(result)

    return f"The answer is {result}."


@app.post("/v1/answer")
async def answer(data: dict):
    query = data.get("query", "")
    assets = data.get("assets", [])  # safe handling

    result = solve_math(query)

    if result:
        return {"output": result}

    return {"output": "Unable to process the query."}