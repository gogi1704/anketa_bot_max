from fastapi import Request
from api.api_funs import pay_completed, pay_canceled
from max.bot_instace import dp

@dp.webhook_post("/bot/internal/payment-success")
async def payment_success(request: Request):
    data = await request.json()
    user_id = int(data.get("user_id"))

    await pay_completed(user_id)
    return {"ok": True}


@dp.webhook_post("/bot/internal/payment-canceled")
async def payment_canceled(request: Request):
    data = await request.json()
    user_id = int(data.get("user_id"))

    await pay_canceled(user_id)
    return {"ok": True}