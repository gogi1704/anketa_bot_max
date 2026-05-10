from aiohttp import web
from api.api_funs import pay_completed, pay_canceled
from max.max_bot_main import bot
routes = web.RouteTableDef()


@routes.post("/internal/payment-success")
async def payment_success(request):
    data = await request.json()
    user_id = data.get("user_id")

    print(f"PAYMENT SUCCESS for user: {user_id}")
    await pay_completed(user_id, bot)

    return web.json_response({"ok": True})


@routes.post("/internal/payment-canceled")
async def payment_canceled(request):
    data = await request.json()
    user_id = data.get("user_id")

    print(f"PAYMENT SUCCESS for user: {user_id}")
    await pay_canceled(user_id,bot)

    return web.json_response({"ok": True})


