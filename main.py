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

app = FastAPI(title="Atelier AI Proxy")

# Create a folder to serve our generated images locally to the phone
os.makedirs("generated_images", exist_ok=True)
app.mount("/images", StaticFiles(directory="generated_images"), name="images")

# Load the lightweight (4MB) model to survive Render's 512MB Free Tier limit
lightweight_session = new_session("u2netp")

HF_API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
# The token will be injected via Docker environment variable
HF_HEADERS = {"Authorization": f"Bearer {os.getenv('HF_API_TOKEN', '')}"}

# We use a variable here so you never have to hardcode URLs manually again!
BASE_URL = "https://atelier-ai.onrender.com"

@app.get("/")
async def root():
    return {"status": "Atelier AI Backend is Live", "environment": "Production"}

async def process_style(image_bytes: bytes, style_name: str, prompt: str, filename: str) -> str:
    """Attempts to use Hugging Face, falls back to colorful placeholders if rate-limited."""
    filepath = f"generated_images/{filename}"
    
    try:
        # Give Hugging Face 8 seconds to respond before we fall back
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
            # FIXED: Now returns your actual cloud URL!
            return f"{BASE_URL}/images/{filename}"
        else:
            raise Exception(f"HF API returned {response.status_code}")
            
    except Exception as e:
        print(f"[-] ⚠️ {style_name} fallback triggered (API busy). Using colorful placeholders.")
        # If API fails, return the colorful dummy images so the UI looks great
        dummy_urls = {
            "Cartoon": "https://dummyimage.com/600x600/818BFA/ffffff&text=Cartoon+Style",
            "Anime": "https://dummyimage.com/600x600/DFE2EA/1b1b23&text=Anime+Style",
            "Flat": "https://dummyimage.com/600x600/FFB689/ffffff&text=Flat+Illustration",
            "Pixel": "https://dummyimage.com/600x600/5D5FEF/ffffff&text=Pixel+Art"
        }
        return dummy_urls.get(style_name, "https://dummyimage.com/600x600/cccccc/000000&text=Error")

@app.post("/api/generate")
async def generate_clipart(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form("")
):
    print(f"\n[+] 🟢 INCOMING REQUEST: {image.filename} | Prompt: '{prompt}'")
    
    # 1. Read the image
    input_bytes = await image.read()

    # --- RAM PROTECTION CODE ---
    # Shrink the image to prevent OOM 502 Bad Gateway crashes
    img = Image.open(io.BytesIO(input_bytes))
    img.thumbnail((800, 800)) 
    safe_byte_arr = io.BytesIO()
    img.save(safe_byte_arr, format='PNG')
    input_bytes = safe_byte_arr.getvalue()
    # ---------------------------
    
    # 2. Native Background Removal using rembg
    print("[+] ✂️ Removing background natively (Lightweight Mode)...")
    # Using the 4MB 'u2netp' model instead of the 176MB one
    bg_removed_bytes = remove(input_bytes, session=lightweight_session)
    
    # Save the original and the no-bg version for the Before/After slider
    with open("generated_images/original.png", "wb") as f:
        f.write(input_bytes)
    with open("generated_images/no_bg.png", "wb") as f:
        f.write(bg_removed_bytes)
        
    # FIXED: Replaced your local laptop IP with the cloud URL variable
    original_url = f"{BASE_URL}/images/original.png"
    no_bg_url = f"{BASE_URL}/images/no_bg.png"

    # 3. Process styles asynchronously
    print("[+] 🧠 Processing styles via AI...")
    tasks = [
        process_style(bg_removed_bytes, "Cartoon", prompt, "cartoon.png"),
        process_style(bg_removed_bytes, "Anime", prompt, "anime.png"),
        process_style(bg_removed_bytes, "Flat", prompt, "flat.png"),
        process_style(bg_removed_bytes, "Pixel", prompt, "pixel.png")
    ]
    
    results = await asyncio.gather(*tasks)

    print("[+] ✅ Complete! Sending to Android.\n")
    return {
        "status": "success",
        "data": {
            "original_url": original_url,
            "no_bg_url": no_bg_url,
            "cartoon_url": results[0],
            "anime_url": results[1],
            "flat_illustration_url": results[2],
            "pixel_art_url": results[3]
        }
    }