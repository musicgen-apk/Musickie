from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os

# Inisialisasi aplikasi FastAPI
app = FastAPI(title="KIE.AI Music Generator Render")

# Konfigurasi API KIE.AI (dari variabel lingkungan Render)
KIE_API_URL = "https://api.kie.ai/api/v1/generate"
KIE_TOKEN = os.getenv("KIE_AI_TOKEN")
DEFAULT_CALLBACK = os.getenv("DEFAULT_CALLBACK_URL", "https://your-callback-url.com")

# Model validasi input
class MusicRequest(BaseModel):
    prompt: str
    style: str
    title: str
    callBackUrl: str = ""

# Servir frontend statis
app.mount("/static", StaticFiles(directory="./frontend"), name="static")

# Halaman utama
@app.get("/")
async def root():
    return FileResponse("./frontend/index.html")

# Endpoint generate musik
@app.post("/api/generate")
async def generate_music(req: MusicRequest):
    if not KIE_TOKEN:
        raise HTTPException(status_code=500, detail="KIE_AI_TOKEN belum diatur di Render!")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                KIE_API_URL,
                headers={
                    "Authorization": f"Bearer {KIE_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": req.prompt,
                    "customMode": True,
                    "instrumental": True,
                    "model": "V4",
                    "callBackUrl": req.callBackUrl if req.callBackUrl else DEFAULT_CALLBACK,
                    "style": req.style,
                    "title": req.title,
                    "negativeTags": "",
                    "vocalGender": "m",
                    "styleWeight": 0.65,
                    "weirdnessConstraint": 0.65,
                    "audioWeight": 0.65,
                    "personaId": "",
                    "personaModel": "style_persona"
                }
            )

            if response.status_code == 200:
                return {"status": "SUCCESS", "data": response.json()}
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="API KIE.AI tidak mendukung metode GET (kami pakai POST)")
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Error dari KIE.AI: {response.text}")
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Kesalahan koneksi: {str(e)}")
