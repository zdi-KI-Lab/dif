from fastapi import APIRouter, File, UploadFile, Form
from schemas.analysis import AnalysisRequest
from services.llm import analyze_text
from services.sightengine import analyze_media
from core.logger import logger

router = APIRouter()

@router.post("/analyze")
async def api_analyze_text(request: AnalysisRequest):
    logger.info(f"\n{'='*20} NEUE ANALYSE-ANFRAGE {'='*20}")
    logger.info(f"EINGEREICHTER TEXT:\n{request.text}\n{'-'*40}")
    return await analyze_text(request.text, request.user_choice)

@router.post("/analyze-image")
async def api_analyze_image(file: UploadFile = File(None), url: str = Form(None)):
    logger.info(f"\n{'='*20} NEUE BILD-ANALYSE {'='*20}")
    return await analyze_media(file, url)