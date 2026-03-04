from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import httpx
import os
import json
from datetime import datetime

# Inisialisasi Aplikasi
app = FastAPI(title="Musickie FULL - Lirik, Foto & Durasi", version="2.0")

# Konfigurasi Folder & Variabel Lingkungan
if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists("static"):
    os.makedirs("static")

KIE_API_URL = "https://api.kie.ai/api/v1/generate"
KIE_TOKEN = os.getenv("KIE_AI_TOKEN")
if not KIE_TOKEN:
    raise RuntimeError("KIE_AI_TOKEN HARUS DIATUR DI RENDER!")

# Servir Frontend
app.mount("/static", StaticFiles(directory="./static"), name="static")
@app.get("/")
async def root():
    return FileResponse("./static/index.html")

# Model Validasi Input
class MusicRequest(BaseModel):
    prompt: str
    customMode: bool = True
    instrumental: bool = True
    model: str = "V5"
    style: str
    title: str
    callBackUrl: str = "https://musickie.onrender.com/api/receive-result"
    negativeTags: str = ""
    vocalGender: str = "m"
    styleWeight: float = 0.65
    weirdnessConstraint: float = 0.65
    audioWeight: float = 0.65
    personaId: str = ""

# Model untuk Menerima Hasil dari KIE.AI
class KIEResponse(BaseModel):
    code: int
    msg: str
    data: dict

# Penyimpanan Data Musik (Permanen di File)
def save_music_data(data: dict):
    with open("data/music_database.json", "r+") as f:
        db = json.load(f)
        db[data["task_id"]] = data
        f.seek(0)
        json.dump(db, f, indent=2)

def load_music_data():
    if not os.path.exists("data/music_database.json"):
        with open("data/music_database.json", "w") as f:
            json.dump({}, f)
    with open("data/music_database.json", "r") as f:
        return json.load(f)

# Endpoint Generate Musik
@app.post("/api/generate-music")
async def generate_music(req: MusicRequest):
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
                    "customMode": req.customMode,
                    "instrumental": req.instrumental,
                    "model": req.model,
                    "style": req.style,
                    "title": req.title,
                    "callBackUrl": req.callBackUrl,
                    "negativeTags": req.negativeTags,
                    "vocalGender": req.vocalGender,
                    "styleWeight": req.styleWeight,
                    "weirdnessConstraint": req.weirdnessConstraint,
                    "audioWeight": req.audioWeight,
                    "personaId": req.personaId
                }
            )
        result = response.json()
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=result["msg"])
        
        # Simpan Task ID Awal
        task_id = result["data"]["task_id"]
        initial_data = {
            "task_id": task_id,
            "title": req.title,
            "style": req.style,
            "created_at": datetime.now().isoformat(),
            "status": "PROCESSING",
            "lyrics": "",
            "cover_url": "",
            "duration": 0.0,
            "audio_url": "",
            "image_url": "",
            "tags": req.style.split(",")
        }
        save_music_data(initial_data)
        return JSONResponse(content={"status": "SUCCESS", "task_id": task_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal Generate: {str(e)}")

# Endpoint Terima Hasil dari KIE.AI (Callback)
@app.post("/api/receive-result")
async def receive_result(request: Request):
    try:
        data = await request.json()
        task_id = data["task_id"]
        music_db = load_music_data()
        
        # Update Semua Detail dari KIE.AI
        music_db[task_id].update({
            "status": "COMPLETED",
            "lyrics": data["data"][0]["lyrics"],
            "cover_url": data["data"][0]["image_url"],
            "duration": data["data"][0]["duration"],
            "audio_url": data["data"][0]["audio_url"],
            "image_url": data["data"][0]["image_url"],
            "style_detail": data["data"][0]["tags"],
            "download_url": data["data"][0]["download_url"]
        })
        
        with open("data/music_database.json", "w") as f:
            json.dump(music_db, f, indent=2)
        return JSONResponse(content={"status": "RECEIVED"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal Terima Hasil: {str(e)}")

# Endpoint Ambil Daftar Musik
@app.get("/api/music-list")
async def get_music_list():
    return JSONResponse(content=load_music_data())

# Endpoint Unduh Lirik
@app.get("/api/download-lyrics/{task_id}")
async def download_lyrics(task_id: str):
    music_db = load_music_data()
    if task_id not in music_db:
        raise HTTPException(status_code=404, detail="Musik Tidak Ditemukan")
    
    lyrics = music_db[task_id]["lyrics"]
    return StreamingResponse(
        iter([lyrics.encode()]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={task_id}_lyrics.txt"}
    )

# Endpoint Unduh Foto Sampul
@app.get("/api/download-cover/{task_id}")
async def download_cover(task_id: str):
    music_db = load_music_data()
    if task_id not in music_db:
        raise HTTPException(status_code=404, detail="Musik Tidak Ditemukan")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(music_db[task_id]["cover_url"])
            return StreamingResponse(
                iter([response.content]),
                media_type="image/jpeg",
                headers={"Content-Disposition": f"attachment; filename={task_id}_cover.jpg"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal Unduh Foto: {str(e)}")

# Endpoint Unduh Audio
@app.get("/api/download-audio/{task_id}")
async def download_audio(task_id: str):
    music_db = load_music_data()
    if task_id not in music_db:
        raise HTTPException(status_code=404, detail="Musik Tidak Ditemukan")
    
    audio_url = music_db[task_id]["audio_url"]
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url)
            return StreamingResponse(
                iter([response.content]),
                media_type="audio/mpeg",
                headers={"Content-Disposition": f"attachment; filename={task_id}_music.mp3"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal Unduh Audio: {str(e)}")
