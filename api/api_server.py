from aiohttp import web

routes = web.RouteTableDef()


@routes.post("/internal/payment-success")
async def payment_success(request):

    data = await request.json()

    user_id = data.get("user_id")

    print(f"PAYMENT SUCCESS for user: {user_id}")

    # 🔥 ВОТ ТУТ ОСНОВНАЯ ЛОГИКА:
    await give_access(user_id)

    return web.json_response({"ok": True})


async def give_access(user_id: int):
    # 1. записать в БД
    # 2. включить подписку
    # 3. отправить сообщение пользователю

    print(f"Access granted to {user_id}")