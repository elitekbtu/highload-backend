from fastapi import FastAPI
from typing import Union

app = FastAPI()


@app.get("/api/quote/{id}")
def get_quote(id: int) -> dict[str, Union[int, str]]:
    return {"id": id, "pair": "USDKZT", "bid": 533.14}


@app.get("/api/quotes")
def get_quotes(n: int = 1) -> list[dict[str, Union[int, str]]]:
    return [{"id": id, "pair": "USDKZT", "bid": 533.14} for id in range(1, n + 1)]
