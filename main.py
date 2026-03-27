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

# 🚨 THE CIRCUIT BREAKER
# If HF rate-limits us once, we trip this switch to skip the 8-second waits for the other styles
API_BLOCKED = False 

@app.get("/")
async def root():
    return {"status": "Atelier AI Backend is Live", "environment": "Production"}

async def process_style(image_bytes: bytes, style_name: str, prompt: str, filename: str) -> str:
    global API_BLOCKED
    filepath = f"generated_images/{filename}"
    
    # If the circuit breaker is tripped, skip the network call entirely!
    if API_BLOCKED:
        print(f"[-] ⚡ Circuit Breaker open! Skipping {style_name} to save time.")
        shutil.copy("generated_images/no_bg.png", filepath)
        return f"{BASE_URL}/images/{filename}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                HF_API_URL, 
                headers=HF_HEADERS, 
                content=image_bytes,
                timeout=4.0 # Reduced from 8.0 to fail faster and keep UX snappy
            )
            
        if response.status_code == 200:
            print(f"[+] ✨ HF Success for {style_name}!")
            with open(filepath, "wb") as f:
                f.write(response.content)
            return f"{BASE_URL}/images/{filename}"
        else:
            # If we get a 429 Rate Limit or 503 Service Unavailable, trip the breaker
            if response.status_code in [429, 503]:
                API_BLOCKED = True
            raise Exception(f"HF API returned {response.status_code}")
            
    except Exception as e:
        print(f"[-] ⚠️ {style_name} fallback. Graceful degradation: using background-removed image.")
        shutil.copy("generated_images/no_bg.png", filepath)
        return f"{BASE_URL}/images/{filename}"

@app.post("/api/generate")
async def generate_clipart(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form("")
):
    global API_BLOCKED
    API_BLOCKED = False # Reset the circuit breaker for every new user request
    
    print(f"\n[+] 🟢 INCOMING REQUEST: {image.filename}")
    
    input_bytes = await image.read()

    # RAM PROTECTION: Shrink image and force garbage collection
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

    print("[+] 🧠 Processing styles sequentially...")
    
    # Process sequentially. If Cartoon fails, Anime, Flat, and Pixel will skip instantly!
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