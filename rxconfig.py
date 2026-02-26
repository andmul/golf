import reflex as rx
import os

render_url = os.environ.get("RENDER_EXTERNAL_URL")

# Build CORS allowed origins
cors_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]
if render_url:
    cors_allowed_origins.append(render_url)

config = rx.Config(
    app_name="golf_reflex",
    # If render_url is None, Reflex will use localhost defaults appropriately
    api_url=render_url if render_url else "http://localhost:8000",
    deploy_url=render_url,
    cors_allowed_origins=cors_allowed_origins,
    backend_port=8000,
    frontend_port=3000,
    # Enable these for production if needed, but allow dev locally
    env=rx.Env.PROD if render_url else rx.Env.DEV,
)
