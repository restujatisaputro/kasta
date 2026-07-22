from fastapi import APIRouter

from kasta_api.api.routes import health
from kasta_api.modules.accounting import router as accounting
from kasta_api.modules.auth import router as auth
from kasta_api.modules.businesses import router as businesses
from kasta_api.modules.inventory import router as inventory
from kasta_api.modules.mentors.access_router import (
    business_access_router,
    mentor_access_router,
    support_access_router,
)
from kasta_api.modules.mentors.router import router as mentors
from kasta_api.modules.notifications.router import router as notifications
from kasta_api.modules.obligations import router as obligations
from kasta_api.modules.ocr import router as ocr
from kasta_api.modules.privacy import router as privacy
from kasta_api.modules.reports import router as reports
from kasta_api.modules.sync import router as sync
from kasta_api.modules.transactions import router as transactions

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["system"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(businesses.router, tags=["businesses"])
api_router.include_router(inventory, tags=["inventory"])
api_router.include_router(accounting, tags=["accounting"])
api_router.include_router(transactions, tags=["transactions"])
api_router.include_router(ocr, tags=["ocr"])
api_router.include_router(privacy, tags=["privacy"])
api_router.include_router(obligations)
api_router.include_router(reports, tags=["reports"])
api_router.include_router(sync.router)
api_router.include_router(mentors)
api_router.include_router(notifications)
api_router.include_router(mentor_access_router)
api_router.include_router(business_access_router)
api_router.include_router(support_access_router)
