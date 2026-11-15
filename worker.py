"""
worker.py
Root launcher for ResumeMatch AI Background Embedding Worker.
Runs in its own process, completely decoupled from the Flask web server.
"""

from src.services.embedding_worker import main

if __name__ == "__main__":
    main()
