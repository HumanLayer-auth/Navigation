from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import buildings, query

app = FastAPI(title="Navigation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(buildings.router)
app.include_router(query.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
