import http.client
import json
from urllib.parse import urlparse  # Untuk memastikan URL callback valid

# --- KONFIGURASI ---
KIE_TOKEN = "YOUR_ACTUAL_KIE_AI_TOKEN"  # Ganti dengan token kamu
CALLBACK_URL = "https://musickie.onrender.com/api/receive-callback"  # Ganti dengan URL web kamu yang publik

def generate_music():
    conn = http.client.HTTPSConnection("api.kie.ai")
    payload = json.dumps({
        "prompt": "A calm and relaxing piano track with soft melodies",
        "customMode": True,
        "instrumental": True,
        "model": "V4",
        "callBackUrl": CALLBACK_URL,  # URL callback yang benar dan publik
        "style": "Classical",
        "title": "Peaceful Piano Meditation",
        "negativeTags": "",
        "vocalGender": "m",
        "styleWeight": 0.65,
        "weirdnessConstraint": 0.65,
        "audioWeight": 0.65
    })
    
    headers = {
        'Authorization': f'Bearer {KIE_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    conn.request("POST", "/api/v1/generate", payload, headers)
    res = conn.getresponse()
    
    # Cek respon dari KIE.AI
    if res.status == 200:
        data = json.loads(res.read().decode("utf-8"))
        print("✅ Permintaan diterima! Task ID:", data.get("task_id"))
        return data
    elif res.status == 500:
        print("❌ Error Server KIE.AI")
        return None
    else:
        print(f"⚠️ Error {res.status}:", res.read().decode("utf-8"))
        return None

def validate_callback_url(url):
    """Memastikan URL callback adalah HTTPS dan bisa diakses publik"""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Callback URL harus menggunakan HTTPS")
    # Tambahkan pengecekan koneksi jika perlu
    return True

if __name__ == "__main__":
    # Validasi URL callback sebelum kirim
    try:
        validate_callback_url(CALLBACK_URL)
        print("🔍 URL Callback valid!")
        result = generate_music()
        if result:
            print("🎵 Hasil Generate:", result)
    except Exception as e:
        print("❌ Error:", str(e))
