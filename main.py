from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, time, base64, requests

app = FastAPI()

# CORS (for local testing + phone)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for expo/demo; lock down later
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Email provider (Resend) ---
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")

if not RESEND_API_KEY:
    raise RuntimeError("RESEND_API_KEY missing")

# --- Simple in-memory pending request store ---
# pending = {"token": "...", "email": "...", "expires": epoch_seconds}
PENDING = None
# store uploaded images by token until emailed
IMAGES = {}  # token -> bytes


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/request")
async def request_photo(email: str = Form(...)):
    global PENDING
    token = uuid.uuid4().hex
    PENDING = {"token": token, "email": email, "expires": time.time() + 25}  # 25s window
    return {"status": "queued", "token": token}


@app.get("/next")
def next_request():
    global PENDING
    if not PENDING:
        return {"has_request": False}
    if time.time() > PENDING["expires"]:
        PENDING = None
        return {"has_request": False}
    return {"has_request": True, "token": PENDING["token"]}


@app.post("/upload")
async def upload_image(request: Request):
    """
    ESP32 uploads raw jpeg bytes.
    Requires header: X-Token: <token>
    """
    global PENDING
    token = request.headers.get("x-token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing X-Token header")

    data = await request.body()
    if not data or len(data) < 500:
        raise HTTPException(status_code=400, detail="Invalid image body")

    IMAGES[token] = data

    # If this token matches current pending request, send now
    if PENDING and PENDING["token"] == token:
        email = PENDING["email"]
        PENDING = None
        await send_email_with_attachment(email, data)

    return {"status": "image received", "bytes": len(data)}


async def send_email_with_attachment(to_email: str, image_bytes: bytes):
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    filename = f"spacepoint_{uuid.uuid4().hex}.jpg"

    payload = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": "Your SpacePoint Satellite Photo 🚀",
        "text": "Thank you for visiting SpacePoint 🚀\n\nAttached is your satellite camera photo.",
        "attachments": [{"filename": filename, "content": b64}],
    }

    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    if r.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Email API failed: {r.status_code} {r.text}")
