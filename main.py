from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import os
import uuid
import requests

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)



app = FastAPI()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")  # default works for testing

if not RESEND_API_KEY:
    raise RuntimeError("RESEND_API_KEY is not set in environment variables")

LAST_IMAGE = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    global LAST_IMAGE
    # Ensure it's jpeg-ish (optional)
    data = await file.read()
    if len(data) < 200:
        raise HTTPException(status_code=400, detail="Image too small / invalid")
    LAST_IMAGE = data
    return {"status": "image received", "bytes": len(LAST_IMAGE)}


@app.post("/send")
async def send_email(email: str = Form(...)):
    if LAST_IMAGE is None:
        raise HTTPException(status_code=400, detail="No image captured yet")

    # Resend needs base64 content for attachments
    import base64
    b64 = base64.b64encode(LAST_IMAGE).decode("utf-8")

    filename = f"spacepoint_{uuid.uuid4().hex}.jpg"

    payload = {
        "from": EMAIL_FROM,
        "to": [email],
        "subject": "Your SpacePoint Satellite Photo 🚀",
        "text": "Thank you for visiting SpacePoint 🚀\n\nAttached is your satellite camera photo.",
        "attachments": [
            {
                "filename": filename,
                "content": b64
            }
        ],
    }

    r = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )

    if r.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Resend failed: {r.status_code} {r.text}")

    return {"status": "email sent"}
