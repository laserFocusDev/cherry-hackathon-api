from fastapi import FastAPI
import re

app = FastAPI()


def extract_expression(query: str):
    match = re.search(r'(\d+(?:\s*[\+\-\*\/]\s*\d+)+)', query)
    if match:
        return match.group(1)
    return None


def safe_eval(expr: str):
    try:
        return eval(expr)
    except:
        return None


def get_operation(expr: str):
    if "+" in expr:
        return "sum"
    elif "-" in expr:
        return "difference"
    elif "*" in expr:
        return "product"
    elif "/" in expr:
        return "quotient"
    return "result"


def solve_math(query: str):
    expr = extract_expression(query)
    if not expr:
        return None

    result = safe_eval(expr)
    if result is None:
        return None

    # clean float
    if isinstance(result, float) and result.is_integer():
        result = int(result)

    operation = get_operation(expr)

    return f"The {operation} is {result}."


@app.post("/v1/answer")
async def answer(data: dict):
    query = data.get("query", "")
    assets = data.get("assets", [])

    result = solve_math(query)

    if result:
        return {"output": result}

    return {"output": "Unable to process the query."}