from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_billing import router as billing_router
from app.db.session import Base, engine

app = FastAPI(title="Billing Service", version="0.1.0")
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(billing_router)
