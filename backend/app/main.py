from fastapi import FastAPI

app = FastAPI(title="RoadRupee API")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
