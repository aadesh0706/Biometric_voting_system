from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict
import os
import io
import json
import time
import shutil
import pickle
import numpy as np
from datetime import datetime, timedelta
import face_recognition
from cryptography.fernet import Fernet
import jwt

BASE = "database"
os.makedirs(BASE, exist_ok=True)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "30"))
ENC_KEY = os.getenv("ENC_KEY")

if not ENC_KEY:
    # Generate a key once and set it as ENC_KEY env var for real use.
    ENC_KEY = Fernet.generate_key().decode("utf-8")

fernet = Fernet(ENC_KEY.encode("utf-8"))

app = FastAPI(title="Biometric Voting API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)

REQUIRED_EXPRESSIONS = ["neutral", "blink", "smile", "left", "right"]
ENCODINGS_FILE = os.path.join(BASE, "encodings.pkl")
AUDIT_LOG = os.path.join(BASE, "audit_log.jsonl")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))

security = HTTPBearer()

rate_bucket: Dict[str, list] = {}

def _rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60
    bucket = rate_bucket.get(ip, [])
    bucket = [t for t in bucket if now - t < window]
    if len(bucket) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)
    rate_bucket[ip] = bucket


def _log_event(event: str, data: dict):
    payload = {
        "event": event,
        "data": data,
        "time": datetime.utcnow().isoformat() + "Z",
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(payload) + "\n")


def _load_all_encodings():
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def _save_all_encodings(data):
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)


def _compute_encoding_from_bytes(image_bytes: bytes):
    img = face_recognition.load_image_file(io.BytesIO(image_bytes))
    encodings = face_recognition.face_encodings(img)
    if not encodings:
        return None
    return encodings[0]


def _encrypt_encoding(encoding: np.ndarray) -> bytes:
    raw = encoding.astype(np.float32).tobytes()
    return fernet.encrypt(raw)


def _decrypt_encoding(token: bytes) -> np.ndarray:
    raw = fernet.decrypt(token)
    arr = np.frombuffer(raw, dtype=np.float32)
    return arr


def _issue_token(aadhaar: str, name: str):
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MIN)
    payload = {"sub": aadhaar, "name": name, "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _require_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class VoteRequest(BaseModel):
    candidate: str


@app.post("/register")
async def register_voter(
    request: Request,
    name: str = Form(...),
    aadhaar: str = Form(...),
    neutral: UploadFile = File(...),
    blink: UploadFile = File(...),
    smile: UploadFile = File(...),
    left: UploadFile = File(...),
    right: UploadFile = File(...),
):
    _rate_limit(request)
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        raise HTTPException(status_code=400, detail="Invalid Aadhaar number")

    voter_folder = os.path.join(BASE, aadhaar)
    meta_file = os.path.join(voter_folder, "meta.json")

    if os.path.exists(meta_file):
        raise HTTPException(status_code=409, detail="Voter already registered")

    if os.path.exists(voter_folder):
        shutil.rmtree(voter_folder)
    os.makedirs(voter_folder, exist_ok=True)

    files = {
        "neutral": neutral,
        "blink": blink,
        "smile": smile,
        "left": left,
        "right": right,
    }

    encodings = []
    for key in REQUIRED_EXPRESSIONS:
        file = files[key]
        data = await file.read()
        encoding = _compute_encoding_from_bytes(data)
        if encoding is None:
            shutil.rmtree(voter_folder)
            raise HTTPException(status_code=400, detail=f"No face detected in {key} image")
        encodings.append(encoding)

    avg_encoding = np.mean(encodings, axis=0).astype(np.float32)

    all_encodings = _load_all_encodings()
    for existing_aadhaar, existing_enc_token in all_encodings.items():
        existing_encoding = _decrypt_encoding(existing_enc_token)
        distance = np.linalg.norm(avg_encoding - existing_encoding)
        if distance <= 0.45:
            shutil.rmtree(voter_folder)
            raise HTTPException(status_code=409, detail="Duplicate voter detected")

    enc_token = _encrypt_encoding(avg_encoding)
    with open(os.path.join(voter_folder, "encoding.enc"), "wb") as f:
        f.write(enc_token)

    metadata = {"name": name, "aadhaar": aadhaar, "voted": False}
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=4)

    all_encodings[aadhaar] = enc_token
    _save_all_encodings(all_encodings)

    _log_event("register", {"aadhaar": aadhaar, "name": name})

    return JSONResponse({"status": "ok", "message": "Registration completed"})


@app.post("/authenticate")
async def authenticate_voter(
    request: Request,
    aadhaar: str = Form(...),
    image: UploadFile = File(...),
):
    _rate_limit(request)
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        raise HTTPException(status_code=400, detail="Invalid Aadhaar number")

    voter_folder = os.path.join(BASE, aadhaar)
    encoding_file = os.path.join(voter_folder, "encoding.enc")
    meta_file = os.path.join(voter_folder, "meta.json")

    if not os.path.exists(encoding_file) or not os.path.exists(meta_file):
        raise HTTPException(status_code=404, detail="Voter not found")

    with open(meta_file, "r") as f:
        meta = json.load(f)

    if meta.get("voted"):
        raise HTTPException(status_code=403, detail="Voter has already voted")

    with open(encoding_file, "rb") as f:
        known_encoding = _decrypt_encoding(f.read())

    data = await image.read()
    captured_encoding = _compute_encoding_from_bytes(data)
    if captured_encoding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    distance = np.linalg.norm(captured_encoding - known_encoding)
    if distance < 0.45:
        token = _issue_token(aadhaar, meta.get("name", ""))
        _log_event("authenticate", {"aadhaar": aadhaar, "result": "ok"})
        return JSONResponse({"status": "ok", "name": meta.get("name"), "token": token})

    _log_event("authenticate", {"aadhaar": aadhaar, "result": "fail"})
    raise HTTPException(status_code=401, detail="Face not recognized")


@app.post("/vote")
async def cast_vote(
    request: Request,
    vote: VoteRequest,
    payload=Depends(_require_token),
):
    _rate_limit(request)
    aadhaar = payload.get("sub")
    if not aadhaar:
        raise HTTPException(status_code=401, detail="Invalid token")

    candidate = vote.candidate
    if candidate not in ["Candidate A", "Candidate B", "Candidate C", "Candidate D"]:
        raise HTTPException(status_code=400, detail="Invalid candidate")

    voter_folder = os.path.join(BASE, aadhaar)
    meta_file = os.path.join(voter_folder, "meta.json")

    if not os.path.exists(meta_file):
        raise HTTPException(status_code=404, detail="Voter not found")

    with open(meta_file, "r") as f:
        meta = json.load(f)

    if meta.get("voted"):
        raise HTTPException(status_code=403, detail="Vote already cast")

    meta["voted"] = True
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=4)

    log_path = os.path.join(BASE, "vote_log.txt")
    with open(log_path, "a") as log:
        log.write(
            f"Aadhaar: {aadhaar}, Name: {meta.get('name')}, Candidate: {candidate}, Voted: True, Time: {datetime.now()}\n"
        )

    _log_event("vote", {"aadhaar": aadhaar, "candidate": candidate})

    return JSONResponse({"status": "ok", "message": "Vote recorded"})


@app.post("/admin/login")
async def admin_login(username: str = Form(...), password: str = Form(...)):
    if username != ADMIN_USER or password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    token = _issue_token("admin", "admin")
    return JSONResponse({"token": token})


@app.get("/admin/registrations")
async def list_registrations(payload=Depends(_require_token)):
    if payload.get("sub") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    registrations = []
    if os.path.exists(BASE):
        for aadhaar in os.listdir(BASE):
            folder = os.path.join(BASE, aadhaar)
            meta_file = os.path.join(folder, "meta.json")
            if os.path.exists(meta_file):
                with open(meta_file, "r") as f:
                    registrations.append(json.load(f))

    return JSONResponse({"registrations": registrations})


@app.get("/admin/votes")
async def list_votes(payload=Depends(_require_token)):
    if payload.get("sub") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    log_path = os.path.join(BASE, "vote_log.txt")
    if not os.path.exists(log_path):
        return JSONResponse({"votes": []})

    with open(log_path, "r") as f:
        lines = f.readlines()
    return JSONResponse({"votes": lines})


@app.get("/admin/export/votes")
async def export_votes(payload=Depends(_require_token)):
    if payload.get("sub") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    log_path = os.path.join(BASE, "vote_log.txt")
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="No votes")

    return FileResponse(log_path, media_type="text/plain", filename="vote_log.txt")
