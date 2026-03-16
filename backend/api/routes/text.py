from fastapi import APIRouter
from schemas.text import GenerationRequest
from services.llm import generate_fake_text
from core.logger import logger

router = APIRouter()

@router.post("/generate-fake")
async def api_generate_fake(request: GenerationRequest):
    logger.info(f"\n{'='*20} NEUE TEXT GENERIERUNG {'='*20}")
    return await generate_fake_text(
        request.thema, request.zielgruppe, request.emotion, request.strategie
    )