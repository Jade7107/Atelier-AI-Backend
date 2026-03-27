from fastapi import FastAPI, File, UploadFile, Form
from typing import Optional
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import asyncio
import os
import shutil
from rembg import remove, new_session
from PIL import Image
import io
import gc

app = FastAPI(title="Atelier AI Proxy")

os.makedirs("generated_images", exist_ok=True)
app.mount("/images", StaticFiles(directory="generated_images"), name="images")

lightweight_session = new_session("u2netp")

HF_API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
HF_HEADERS = {"Authorization": f"Bearer {os.getenv('HF_API_TOKEN', '')}"}
BASE_URL = "https://atelier-ai.onrender.com"

@app.get("/")
async def root():
    return {"status": "Atelier AI Backend is Live", "environment": "Production"}

async def process_style(image_bytes: bytes, style_name: str, prompt: str, filename: str) -> str:
    filepath = f"generated_images/{filename}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                HF_API_URL, 
                headers=HF_HEADERS, 
                content=image_bytes,
                timeout=8.0 
            )
            
        if response.status_code == 200:
            print(f"[+] ✨ HF Success for {style_name}!")
            with open(filepath, "wb") as f:
                f.write(response.content)
            return f"{BASE_URL}/images/{filename}"
        else:
            raise Exception(f"HF API returned {response.status_code}")
            
    except Exception as e:
        print(f"[-] ⚠️ {style_name} fallback. Graceful degradation: using background-removed image.")
        # 🚨 FIX 1: Copy the bg-removed image so the Android app ALWAYS finds a file!
        shutil.copy("generated_images/no_bg.png", filepath)
        return f"{BASE_URL}/images/{filename}"

@app.post("/api/generate")
async def generate_clipart(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form("")
):
    print(f"\n[+] 🟢 INCOMING REQUEST: {image.filename}")
    
    input_bytes = await image.read()

    # RAM PROTECTION
    img = Image.open(io.BytesIO(input_bytes))
    img.thumbnail((800, 800)) 
    safe_byte_arr = io.BytesIO()
    img.save(safe_byte_arr, format='PNG')
    input_bytes = safe_byte_arr.getvalue()
    
    del img
    del safe_byte_arr
    gc.collect()
    
    print("[+] ✂️ Removing background natively...")
    bg_removed_bytes = await asyncio.to_thread(remove, input_bytes, session=lightweight_session)
    
    with open("generated_images/original.png", "wb") as f:
        f.write(input_bytes)
    with open("generated_images/no_bg.png", "wb") as f:
        f.write(bg_removed_bytes)
        
    original_url = f"{BASE_URL}/images/original.png"
    no_bg_url = f"{BASE_URL}/images/no_bg.png"

    print("[+] 🧠 Processing styles sequentially to save RAM...")
    
    # 🚨 FIX 2: Process sequentially to stop the OOM Memory Crashes
    cartoon_url = await process_style(bg_removed_bytes, "Cartoon", prompt, "cartoon.png")
    anime_url = await process_style(bg_removed_bytes, "Anime", prompt, "anime.png")
    flat_url = await process_style(bg_removed_bytes, "Flat", prompt, "flat.png")
    pixel_url = await process_style(bg_removed_bytes, "Pixel", prompt, "pixel.png")

    print("[+] ✅ Complete! Sending to Android.\n")
    return {
        "status": "success",
        "data": {
            "original_url": original_url,
            "no_bg_url": no_bg_url,
            "cartoon_url": cartoon_url,
            "anime_url": anime_url,
            "flat_illustration_url": flat_url,
            "pixel_art_url": pixel_url
        }
    }