import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import STATIC_DIR, CORS_ORIGINS, OUTPUTS_DIR, TEMP_DIR
from core.database import init_global_db
from workers.generate_worker import start_generate_worker, stop_generate_worker
from workers.cleanup_worker import start_cleanup_worker, stop_cleanup_worker
from services.style_service import init_preset_styles

from api.auth_routes import router as auth_router
from api.generate_routes import router as generate_router
from api.user_routes import router as user_router
from api.admin_routes import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    init_global_db()
    init_preset_styles()
    start_generate_worker()
    start_cleanup_worker()
    
    import asyncio
    from core.security import cleanup_user_action_store
    
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(300)
            try:
                cleanup_user_action_store()
            except Exception:
                pass
    
    asyncio.create_task(periodic_cleanup())
    
    print("AI智能作图系统启动完成")
    yield
    stop_generate_worker()
    stop_cleanup_worker()
    print("AI智能作图系统已关闭")


app = FastAPI(title="AI智能作图系统", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(generate_router)
app.include_router(user_router)
app.include_router(admin_router)


@app.get("/")
async def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/admin")
async def admin_page():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


app.mount("/static/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    from core.config import SERVER_HOST, SERVER_PORT
    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
