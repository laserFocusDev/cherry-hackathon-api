import re
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any

app = FastAPI()


def extract_expression(query: str):
    # Normalize unicode minus/multiply signs
    query = query.replace('\u2212', '-').replace('\u00d7', '*').replace('\u00f7', '/')
    # Support decimals in addition to integers
    match = re.search(r'(\d+(?:\.\d+)?(?:\s*[\+\-\*\/]\s*\d+(?:\.\d+)?)+)', query)
    if match:
        return match.group(1)
    return None


def safe_eval(expr: str):
    # Remove all spaces before eval
    expr_clean = re.sub(r'\s+', '', expr)
    try:
        result = eval(expr_clean, {"__builtins__": {}}, {})
        return result
    except Exception:
        return None


def get_operation(expr: str):
    # Strip spaces to reliably detect operator
    expr_clean = re.sub(r'\s+', '', expr)
    if '+' in expr_clean:
        return "sum"
    elif '-' in expr_clean:
        return "difference"
    elif '*' in expr_clean:
        return "product"
    elif '/' in expr_clean:
        return "quotient"
    return "result"


def solve_math(query: str):
    expr = extract_expression(query)
    if not expr:
        return None

    result = safe_eval(expr)
    if result is None:
        return None

    # Avoid division by zero or inf/nan
    if isinstance(result, float):
        if result != result or result in (float('inf'), float('-inf')):
            return None
        if result.is_integer():
            result = int(result)
        else:
            result = round(result, 10)

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