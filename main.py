from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import os
from typing import Optional

# Inisialisasi aplikasi FastAPI
app = FastAPI(title="Musickie - Generator Musik KIE.AI")

# Konfigurasi API KIE.AI
KIE_API_URL = "https://api.kie.ai/api/v1/generate"
KIE_TOKEN = os.getenv("KIE_AI_TOKEN")
DEFAULT_CALLBACK = os.getenv("DEFAULT_CALLBACK_URL", "https://musickie.onrender.com/receive-music-result")

# Penyimpanan sementara hasil musik (untuk ditampilkan di frontend)
saved_music = {}

# Model validasi input
class MusicRequest(BaseModel):
    prompt: str
    style: str
    title: str
    callBackUrl: str = ""

class MusicResult(BaseModel):
    title: str
    style: str
    audio_url: str
    status: str
    id: Optional[str] = None

# Servir file frontend
app.mount("/static", StaticFiles(directory="./"), name="static")

@app.get("/")
async def root():
    return FileResponse("./index.html")

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
                result = response.json()
                music_id = result.get("id", str(len(saved_music) + 1))
                saved_music[music_id] = {
                    "title": req.title,
                    "style": req.style,
                    "audio_url": "",
                    "status": "Sedang diproses..."
                }
                return {"status": "SUCCESS", "data": result, "music_id": music_id}
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="API KIE.AI tidak mendukung metode GET")
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Error dari KIE.AI: {response.text}")
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Kesalahan koneksi: {str(e)}")

# Endpoint callback untuk menerima hasil musik
@app.post("/receive-music-result")
async def receive_music_result(result_data: dict):
    music_id = result_data.get("id") or result_data.get("music_id")
    if music_id and music_id in saved_music:
        saved_music[music_id]["audio_url"] = result_data.get("audio_url", "")
        saved_music[music_id]["status"] = "Selesai"
    else:
        new_id = str(len(saved_music) + 1)
        saved_music[new_id] = {
            "title": result_data.get("title", "Musik Tanpa Judul"),
            "style": result_data.get("style", "Tidak Diketahui"),
            "audio_url": result_data.get("audio_url", ""),
            "status": "Selesai"
        }
    print("✅ Hasil musik diterima:", result_data)
    return {"status": "BERHASIL DITERIMA", "data": result_data}

# Endpoint untuk mengambil daftar musik yang sudah dibuat
@app.get("/api/music-list")
async def get_music_list():
    return {"music": saved_music}
