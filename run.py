import os
import sys
from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    port = Config.PORT
    print(f"============================================================")
    print(f"CoalGov-AI: Smart Governance & Compliance Platform")
    print(f"Starting server on http://127.0.0.1:{port}")
    print(f"Database Mode: {'Live MongoDB' if not app.extensions.get('is_mock', False) else 'Fallback Memory'}")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=Config.DEBUG)
