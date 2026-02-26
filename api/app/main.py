from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.recommender import recommend

app = FastAPI(title="Music Recommender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    phrase: str = Field(..., min_length=1, max_length=500)
    n: int = Field(default=5, ge=3, le=5)


class Song(BaseModel):
    title: str
    artist: str
    score: float
    spotify_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/recommend", response_model=list[Song])
def recommend_songs(body: RecommendRequest):
    if not body.phrase.strip():
        raise HTTPException(status_code=400, detail="phrase must not be blank")
    return recommend(body.phrase.strip(), body.n)
