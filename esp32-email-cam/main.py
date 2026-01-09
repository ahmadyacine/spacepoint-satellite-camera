from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from email.message import EmailMessage
import smtplib
import os
import uuid

app = FastAPI()

# ===== Read from Environment Variables =====
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

if not EMAIL_FROM or not EMAIL_PASSWORD:
    raise RuntimeError("EMAIL_FROM or EMAIL_PASSWORD is not set in environment variables")

# Store last received image in memory
LAST_IMAGE = None


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    global LAST_IMAGE
    LAST_IMAGE = await file.read()
    return {"status": "image received"}


@app.post("/send")
async def send_email(email: str = Form(...)):
    if LAST_IMAGE is None:
        raise HTTPException(status_code=400, detail="No image captured yet")

    msg = EmailMessage()
    msg["Subject"] = "Your SpacePoint Satellite Photo 🚀"
    msg["From"] = EMAIL_FROM
    msg["To"] = email

    msg.set_content(
        "Thank you for visiting SpacePoint 🚀\n\n"
        "Attached is your satellite camera photo.\n\n"
        "— SpacePoint Team"
    )

    filename = f"spacepoint_{uuid.uuid4().hex}.jpg"
    msg.add_attachment(LAST_IMAGE, maintype="image", subtype="jpeg", filename=filename)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "email sent"}
