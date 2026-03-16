from fastapi import APIRouter
from schemas.image import ImagePromptRequest, ImageGenRequest
from services.llm import generate_image_prompt
from services.image import generate_flux_image
from core.logger import logger

router = APIRouter()

@router.post("/generate-image-prompt")
async def api_generate_image_prompt(request: ImagePromptRequest):
    logger.info(f"\n{'='*20} NEUE BILD-PROMPT GENERIERUNG {'='*20}")
    midjourney_prompt = await generate_image_prompt(request.schlagzeile, request.text)
    logger.info(f"GENERIERTER PROMPT: {midjourney_prompt}")
    return {"midjourney_prompt": midjourney_prompt}

@router.post("/generate-image-flux")
async def api_generate_image_flux(request: ImageGenRequest):
    logger.info(f"\n{'='*20} STARTE BILD-GENERIERUNG (IONOS FLUX) {'='*20}")
    return await generate_flux_image(request.prompt)