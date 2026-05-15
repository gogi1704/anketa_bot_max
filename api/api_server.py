# from fastapi import APIRouter, Request
# from api.api_funs import pay_completed, pay_canceled
#
#
# router = APIRouter()
#
# @router.post("/internal/payment-success")
# async def payment_success(request: Request):
#
#     data = await request.json()
#     user_id = data.get("user_id")
#
#     print(f"PAYMENT SUCCESS for user: {user_id}")
#
#     await pay_completed(user_id)
#
#     return {"ok": True}
#
#
# @router.post("/internal/payment-canceled")
# async def payment_canceled(request: Request):
#
#     data = await request.json()
#     user_id = data.get("user_id")
#
#     print(f"PAYMENT CANCELED for user: {user_id}")
#
#     await pay_canceled(user_id)
#
#     return {"ok": True}
#
