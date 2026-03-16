from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import image, text, analysis

app = FastAPI(
    title="DiF-Check API", 
    version="2.0",
    root_path="/api",                 
    openapi_url="/openapi.json",        
    docs_url="/docs")                  

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://demokratie-im-feed.de", 
        "https://www.demokratie-im-feed.de",
    ], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(image.router, tags=["Image Generation"])
app.include_router(text.router, tags=["Text Generation"])
app.include_router(analysis.router, tags=["Analysis"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)