from pydantic import BaseModel

class ImagePromptRequest(BaseModel):
    schlagzeile: str
    text: str

class ImageGenRequest(BaseModel):
    prompt: str