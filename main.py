"""
VERITY - Enterprise Document Intelligence & Compliance Agent
Production Entrypoint
"""

import uvicorn
from src.api.app import create_app
from src.api.config import get_api_config

# Create application instance with default/environment configuration
app = create_app()

if __name__ == "__main__":
    config = get_api_config()
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug and config.environment == "development",
        workers=1,
        log_level=config.log_level.lower(),
    )

