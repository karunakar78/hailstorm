from fastapi import FastAPI

from app.api.v1.router import router

app = FastAPI(title="Hailstorm Load Testing Platform", version="0.1.0")

app.include_router(router)
