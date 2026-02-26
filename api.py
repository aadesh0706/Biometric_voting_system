from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import json
from datetime import datetime

BASE = "database"
os.makedirs(BASE, exist_ok=True)

app = FastAPI(title="Biometric Voting API - Fingerprint Based")

# Enable CORS for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    name: str
    aadhaar: str


class AuthenticateRequest(BaseModel):
    aadhaar: str


class VoteRequest(BaseModel):
    aadhaar: str
    candidate: str


def _get_voter_path(aadhaar: str):
    return os.path.join(BASE, aadhaar)


def _get_meta_path(aadhaar: str):
    return os.path.join(_get_voter_path(aadhaar), "meta.json")


def _load_voter_meta(aadhaar: str):
    meta_path = _get_meta_path(aadhaar)
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, "r") as f:
        return json.load(f)


def _save_voter_meta(aadhaar: str, meta: dict):
    voter_path = _get_voter_path(aadhaar)
    os.makedirs(voter_path, exist_ok=True)
    meta_path = _get_meta_path(aadhaar)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=4)


@app.get("/")
async def root():
    return {"message": "Biometric Voting API - Fingerprint Authentication"}


@app.post("/register")
async def register_voter(request: RegisterRequest):
    """
    Register a new voter with Aadhaar number and name.
    Fingerprint authentication is handled on the mobile device.
    """
    aadhaar = request.aadhaar.strip()
    name = request.name.strip()

    # Validate Aadhaar
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        raise HTTPException(status_code=400, detail="Invalid Aadhaar number. Must be 12 digits.")

    # Validate name
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Invalid name.")

    # Check if already registered
    existing_meta = _load_voter_meta(aadhaar)
    if existing_meta:
        raise HTTPException(
            status_code=409,
            detail="Voter already registered with this Aadhaar number."
        )

    # Create voter record
    meta = {
        "name": name,
        "aadhaar": aadhaar,
        "voted": False,
        "registered_at": datetime.now().isoformat(),
    }
    _save_voter_meta(aadhaar, meta)

    return JSONResponse({
        "status": "ok",
        "message": "Registration completed successfully",
        "name": name
    })


@app.post("/authenticate")
async def authenticate_voter(request: AuthenticateRequest):
    """
    Authenticate a voter by Aadhaar number.
    Fingerprint verification is done on the mobile device before calling this endpoint.
    """
    aadhaar = request.aadhaar.strip()

    # Validate Aadhaar
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        raise HTTPException(status_code=400, detail="Invalid Aadhaar number.")

    # Load voter metadata
    meta = _load_voter_meta(aadhaar)
    if not meta:
        raise HTTPException(status_code=404, detail="Voter not registered.")

    # Check if already voted
    if meta.get("voted"):
        raise HTTPException(
            status_code=403,
            detail="You have already cast your vote. Multiple voting is not allowed."
        )

    return JSONResponse({
        "status": "ok",
        "name": meta.get("name"),
        "can_vote": True,
        "message": "Authentication successful"
    })


@app.post("/vote")
async def cast_vote(request: VoteRequest):
    """
    Record a vote for a candidate.
    Fingerprint verification is done on the mobile device before calling this endpoint.
    """
    aadhaar = request.aadhaar.strip()
    candidate = request.candidate.strip()

    # Validate Aadhaar
    if not aadhaar.isdigit() or len(aadhaar) != 12:
        raise HTTPException(status_code=400, detail="Invalid Aadhaar number.")

    # Validate candidate
    if not candidate:
        raise HTTPException(status_code=400, detail="Invalid candidate selection.")

    # Load voter metadata
    meta = _load_voter_meta(aadhaar)
    if not meta:
        raise HTTPException(status_code=404, detail="Voter not registered.")

    # Check if already voted
    if meta.get("voted"):
        raise HTTPException(
            status_code=403,
            detail="Vote already cast. Multiple voting is not allowed."
        )

    # Update voter status
    meta["voted"] = True
    meta["voted_at"] = datetime.now().isoformat()
    _save_voter_meta(aadhaar, meta)

    # Log the vote (anonymously - without linking to candidate)
    log_path = os.path.join(BASE, "vote_log.txt")
    with open(log_path, "a") as log:
        log.write(
            f"Aadhaar: {aadhaar}, Name: {meta.get('name')}, "
            f"Voted: True, Time: {datetime.now()}\n"
        )

    # Store vote tally separately (for anonymous counting)
    tally_path = os.path.join(BASE, "vote_tally.json")
    if os.path.exists(tally_path):
        with open(tally_path, "r") as f:
            tally = json.load(f)
    else:
        tally = {}

    tally[candidate] = tally.get(candidate, 0) + 1

    with open(tally_path, "w") as f:
        json.dump(tally, f, indent=4)

    return JSONResponse({
        "status": "ok",
        "message": "Vote recorded successfully"
    })


@app.get("/results")
async def get_results():
    """
    Get voting results (vote tally by candidate).
    """
    tally_path = os.path.join(BASE, "vote_tally.json")
    if not os.path.exists(tally_path):
        return JSONResponse({"results": {}, "total_votes": 0})

    with open(tally_path, "r") as f:
        tally = json.load(f)

    total_votes = sum(tally.values())

    return JSONResponse({
        "results": tally,
        "total_votes": total_votes
    })
