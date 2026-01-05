from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    banks,
    accounts,
    categories,
    transactions,
    uploads,
    rules,
    analytics,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(banks.router, prefix="/banks", tags=["banks"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
