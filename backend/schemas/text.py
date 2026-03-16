from pydantic import BaseModel

class GenerationRequest(BaseModel):
    thema: str
    zielgruppe: str
    emotion: str
    strategie: str