from app.core.config import get_settings
from app.main import app


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.server.host, port=settings.server.port)
