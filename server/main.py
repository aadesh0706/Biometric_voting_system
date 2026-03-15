from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
import io
import json
import time
import shutil
import pickle
import uuid
import numpy as np
from datetime import datetime, timedelta
import face_recognition
from cryptography.fernet import Fernet, InvalidToken
import jwt
from PIL import Image

BASE = "database"
os.makedirs(BASE, exist_ok=True)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "30"))
ENC_KEY = os.getenv("ENC_KEY")
ENC_KEY_FILE = os.path.join(BASE, "fernet.key")

if ENC_KEY:
    key_bytes = ENC_KEY.encode("utf-8")
elif os.path.exists(ENC_KEY_FILE):
    with open(ENC_KEY_FILE, "rb") as key_file:
        key_bytes = key_file.read().strip()
else:
    key_bytes = Fernet.generate_key()
    with open(ENC_KEY_FILE, "wb") as key_file:
        key_file.write(key_bytes)

fernet = Fernet(key_bytes)

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
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.45"))
LIVENESS_MATCH_THRESHOLD = float(os.getenv("LIVENESS_MATCH_THRESHOLD", "0.47"))
MIN_LIVENESS_FRAMES = int(os.getenv("MIN_LIVENESS_FRAMES", "2"))
MIN_LIVENESS_VARIATION = float(os.getenv("MIN_LIVENESS_VARIATION", "0.015"))
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "960"))

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
        try:
            with open(ENCODINGS_FILE, "rb") as f:
                data = pickle.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            # Corrupt/legacy encoding map should not crash registration.
            return {}
    return {}


def _save_all_encodings(data):
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)


def _prepare_image_for_encoding(image_bytes: bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
    return np.array(image)


def _compute_encoding_from_bytes(image_bytes: bytes):
    img = _prepare_image_for_encoding(image_bytes)
    face_locations = face_recognition.face_locations(img, model="hog")
    if not face_locations:
        return None
    encodings = face_recognition.face_encodings(img, known_face_locations=face_locations)
    if not encodings:
        return None
    return encodings[0]


def _encrypt_encoding(encoding: np.ndarray) -> bytes:
    raw = encoding.astype(np.float32).tobytes()
    return fernet.encrypt(raw)


def _decrypt_encoding(token: bytes) -> np.ndarray:
    if isinstance(token, str):
        token = token.encode("utf-8")
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
    temp_folder = os.path.join(BASE, f".tmp_register_{aadhaar}_{uuid.uuid4().hex[:8]}")

    if os.path.exists(meta_file):
        raise HTTPException(status_code=409, detail="Voter already registered")

    if os.path.exists(voter_folder):
        # Do not delete existing data on retried requests. A timeout on client can
        # overlap with in-progress registration and lead to unintended data loss.
        existing_files = [f for f in os.listdir(voter_folder) if not f.startswith(".")]
        if existing_files:
            raise HTTPException(
                status_code=409,
                detail="Registration already in progress or completed. Try Verify/Login directly.",
            )
        shutil.rmtree(voter_folder)

    os.makedirs(temp_folder, exist_ok=True)

    files = {
        "neutral": neutral,
        "blink": blink,
        "smile": smile,
        "left": left,
        "right": right,
    }

    encodings = []
    try:
        for key in REQUIRED_EXPRESSIONS:
            file = files[key]
            data = await file.read()

            # Save captured registration frames for auditability/debugging.
            image_path = os.path.join(temp_folder, f"{key}.jpg")
            with open(image_path, "wb") as image_file:
                image_file.write(data)

            encoding = _compute_encoding_from_bytes(data)
            if encoding is None:
                raise HTTPException(status_code=400, detail=f"No face detected in {key} image")
            encodings.append(encoding)

        avg_encoding = np.mean(encodings, axis=0).astype(np.float32)

        all_encodings = _load_all_encodings()
        for existing_aadhaar, existing_enc_token in all_encodings.items():
            try:
                existing_encoding = _decrypt_encoding(existing_enc_token)
            except InvalidToken:
                _log_event(
                    "register_warn",
                    {
                        "aadhaar": aadhaar,
                        "existing_aadhaar": existing_aadhaar,
                        "reason": "invalid_encoding_token",
                    },
                )
                continue
            except Exception as decode_error:
                _log_event(
                    "register_warn",
                    {
                        "aadhaar": aadhaar,
                        "existing_aadhaar": existing_aadhaar,
                        "reason": f"decode_error:{type(decode_error).__name__}",
                    },
                )
                continue

            distance = np.linalg.norm(avg_encoding - existing_encoding)
            if distance <= FACE_MATCH_THRESHOLD:
                raise HTTPException(status_code=409, detail="Duplicate voter detected")

        enc_token = _encrypt_encoding(avg_encoding)
        with open(os.path.join(temp_folder, "encoding.enc"), "wb") as f:
            f.write(enc_token)

        metadata = {
            "name": name,
            "aadhaar": aadhaar,
            "voted": False,
            "registered_at": datetime.utcnow().isoformat() + "Z",
            "face_profile": {
                "expressions": REQUIRED_EXPRESSIONS,
                "match_threshold": FACE_MATCH_THRESHOLD,
            },
        }
        with open(os.path.join(temp_folder, "meta.json"), "w") as f:
            json.dump(metadata, f, indent=4)

        if os.path.exists(voter_folder):
            shutil.rmtree(voter_folder)
        os.replace(temp_folder, voter_folder)

        all_encodings[aadhaar] = enc_token
        _save_all_encodings(all_encodings)

        _log_event("register", {"aadhaar": aadhaar, "name": name})

        return JSONResponse({"status": "ok", "message": "Registration completed"})
    except HTTPException:
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder, ignore_errors=True)
        raise
    except Exception as register_error:
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder, ignore_errors=True)
        _log_event(
            "register_error",
            {
                "aadhaar": aadhaar,
                "error": f"{type(register_error).__name__}: {str(register_error)}",
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Registration processing failed on server. Please retry.",
        )


@app.get("/registration-status/{aadhaar}")
async def registration_status(aadhaar: str):
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        raise HTTPException(status_code=400, detail="Invalid Aadhaar number")

    voter_folder = os.path.join(BASE, aadhaar)
    meta_file = os.path.join(voter_folder, "meta.json")

    if not os.path.exists(meta_file):
        return JSONResponse({"registered": False})

    with open(meta_file, "r") as f:
        meta = json.load(f)

    return JSONResponse(
        {
            "registered": True,
            "name": meta.get("name"),
            "aadhaar": meta.get("aadhaar"),
            "voted": bool(meta.get("voted", False)),
        }
    )


@app.post("/authenticate")
async def authenticate_voter(
    request: Request,
    aadhaar: str = Form(...),
    image: UploadFile = File(...),
    liveness_images: Optional[List[UploadFile]] = File(None),
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
        try:
            known_encoding = _decrypt_encoding(f.read())
        except InvalidToken:
            raise HTTPException(
                status_code=500,
                detail="Stored biometric profile is unreadable. Please re-register this voter.",
            )

    data = await image.read()
    captured_encoding = _compute_encoding_from_bytes(data)
    if captured_encoding is None:
        raise HTTPException(status_code=400, detail="No face detected")

    distance = np.linalg.norm(captured_encoding - known_encoding)
    if distance >= FACE_MATCH_THRESHOLD:
        _log_event("authenticate", {"aadhaar": aadhaar, "result": "fail_primary_match"})
        raise HTTPException(status_code=401, detail="Face not recognized")

    if liveness_images:
        if len(liveness_images) < MIN_LIVENESS_FRAMES:
            raise HTTPException(
                status_code=400,
                detail=f"At least {MIN_LIVENESS_FRAMES} liveness frames are required",
            )

        liveness_encodings = []
        liveness_distances = []

        for idx, frame in enumerate(liveness_images):
            frame_bytes = await frame.read()
            frame_encoding = _compute_encoding_from_bytes(frame_bytes)
            if frame_encoding is None:
                raise HTTPException(status_code=400, detail=f"No face detected in liveness frame {idx + 1}")

            frame_distance = float(np.linalg.norm(frame_encoding - known_encoding))
            liveness_distances.append(frame_distance)
            liveness_encodings.append(frame_encoding.astype(np.float32))

        if any(d > LIVENESS_MATCH_THRESHOLD for d in liveness_distances):
            _log_event("authenticate", {"aadhaar": aadhaar, "result": "fail_liveness_match"})
            raise HTTPException(status_code=401, detail="Liveness frames do not match registered face")

        max_variation = 0.0
        for i in range(len(liveness_encodings)):
            for j in range(i + 1, len(liveness_encodings)):
                max_variation = max(
                    max_variation,
                    float(np.linalg.norm(liveness_encodings[i] - liveness_encodings[j])),
                )

        if max_variation < MIN_LIVENESS_VARIATION:
            _log_event("authenticate", {"aadhaar": aadhaar, "result": "fail_liveness_variation"})
            raise HTTPException(
                status_code=401,
                detail="Liveness verification failed. Please follow motion prompts and try again.",
            )

    if distance < FACE_MATCH_THRESHOLD:
        token = _issue_token(aadhaar, meta.get("name", ""))
        _log_event(
            "authenticate",
            {
                "aadhaar": aadhaar,
                "result": "ok",
                "distance": float(distance),
                "liveness_frames": len(liveness_images or []),
            },
        )
        return JSONResponse(
            {
                "status": "ok",
                "name": meta.get("name"),
                "token": token,
                "face_distance": float(distance),
                "liveness_verified": bool(liveness_images),
            }
        )

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
