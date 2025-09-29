"""Web server entry point for Ankicraft."""
import uvicorn
from .settings import WebSettings

def main():
    """Run the web server."""
    settings = WebSettings()
    uvicorn.run(
        "ankicraft.web:app",
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        reload=settings.WEB_DEBUG,
        log_level="info"
    )

if __name__ == "__main__":
    main()