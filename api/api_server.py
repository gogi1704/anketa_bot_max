from fastapi import FastAPI

app = FastAPI()


@app.get("/ping")
async def ping():
    return {"status": "bot api ok"}


@app.post("/internal/payment-success")
async def payment_success(data: dict):

    user_id = data.get("user_id")

    print(f"PAYMENT SUCCESS: {user_id}")

    return {"ok": True}