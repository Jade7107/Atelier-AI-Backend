# Atelier AI - Clipart Generator

A production-quality Android application that transforms user photos into high-fidelity clipart styles. Built for the AI Clipart Generator Assignment.

## 🔗 Submission Links
* **APK Download:** [INSERT APK DRIVE LINK HERE]
* **Screen Recording Walkthrough:** [INSERT VIDEO DRIVE LINK HERE]

## 🚀 Setup & Installation
1. Download the APK from the link above and install it on a physical Android device.
2. Ensure you have an active internet connection.
3. Select an image from your gallery or camera.
4. *Note: The backend is hosted on Render's Free Tier. It may take ~45 seconds to wake up on the very first request.*

## 🛠 Tech Stack & Decisions
* **Frontend:** Native Android (Kotlin, Jetpack Compose). Chosen for optimal mobile UX, smooth animations, and native performance.
* **Backend Proxy:** FastAPI (Python) containerized with Docker and hosted on Render. 
* **Security:** Implemented a backend proxy to securely hide the Hugging Face API tokens, satisfying the strict security requirement to prevent exposed API keys.
* **Image Loading:** `Coil` for asynchronous, memory-safe image fetching and rendering.

## ⚖️ Tradeoffs Made (Decision-Making Under Constraint)
Due to the strict 72-hour time limit and zero-budget constraint, I prioritized UX smoothness and crash prevention over raw generation volume:

1. **The Circuit Breaker Pattern:** Hugging Face's free tier aggressively rate-limits parallel requests. Instead of forcing the user to wait 30+ seconds for a timeout, I implemented a backend circuit breaker. If the API rejects the first style, the backend instantly trips the breaker, skips the remaining external calls, and falls back to a locally processed image. This keeps the "First meaningful UI" speed fast.
2. **Graceful Degradation over Errors:** To maintain a "non-blocking UX", the backend utilizes `rembg` (u2netp lightweight model) for native background removal. If the external AI API is busy, the app gracefully degrades by rendering the background-removed image in the placeholders instead of throwing ugly 404 errors or crashing.
3. **Memory Management vs. Speed:** Render's 512MB RAM limit caused `502 Bad Gateway` OOM crashes during parallel generation. I traded slight processing speed for stability by enforcing sequential API processing and aggressive Python Garbage Collection (`gc.collect()`), entirely eliminating the crashes.

## ✨ Bonus Features Implemented
* **Background Removal:** Native local processing using `rembg`.
* **Before/After Slider:** An interactive compose slider to compare the original image with the background-removed output.
* **Prompt Editor:** Allows users to pass custom hints to the generation endpoint.