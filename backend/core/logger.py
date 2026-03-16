import logging
import os

def setup_logger() -> logging.Logger:
    """Configures and returns the application logger."""
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("logs/LLM_responses.log"),
            logging.StreamHandler() 
        ]
    )
    return logging.getLogger("dif-check")

logger = setup_logger()