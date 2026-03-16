from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    text: str
    user_choice: str