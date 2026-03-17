# Android App + Backend Architecture (Biometric Voting)

## 1. Overview
This project uses an Android app (React Native + Expo) as the client and a Python FastAPI server as the biometric backend.

High-level flow:
1. User registers from Android with Aadhaar, name, and face captures.
2. Backend computes and stores face embeddings (encodings).
3. User verifies identity with fresh face + liveness captures.
4. User votes only after successful biometric verification and token authorization.

The implementation follows "face + liveness + one vote" security checks.

## 2. Android App Stack
App source is in [mobile/App.js](mobile/App.js).

Core libraries used on Android:
1. `expo` / `react-native` / `react`
   - App runtime, UI, navigation/state rendering.
2. `expo-local-authentication`
   - Device biometric prompt (fingerprint/biometric lock).
   - Used before registration, verification, and vote submit.
3. `expo-image-picker`
   - Captures images from device camera.
   - Used for registration expression images and verification liveness images.
4. `expo-image-manipulator`
   - Resizes/compresses captured images before upload.
   - Reduces payload and timeout risk during registration/verification.
5. `@react-native-async-storage/async-storage`
   - Local cache for lightweight app state (voter sync hints, auth flow support).
6. `expo-dev-client`
   - Required for running native Expo modules in development builds.

Config is in [mobile/config.js](mobile/config.js):
- `API_BASE_URL`
- timeout settings for register/auth requests
- liveness prompts and expression keys

## 3. Backend Stack
Backend source is in [server/main.py](server/main.py).

Core libraries used on backend:
1. `fastapi`
   - REST API endpoints and request validation.
2. `uvicorn`
   - ASGI server to run the FastAPI app.
3. `python-multipart`
   - Handles multipart/form-data uploads (face images).
4. `face_recognition`
   - Computes face encodings and face distance matching.
5. `face_recognition_models`
   - Pretrained model data used by `face_recognition`.
6. `dlib` (indirect via face_recognition)
   - Face detection and embedding generation internals.
7. `numpy`
   - Vector math for encoding distance comparisons.
8. `pillow` (`PIL`)
   - Image resizing/preprocessing before encoding.
9. `cryptography` (`Fernet`)
   - Encrypts stored face embeddings (`encoding.enc`).
10. `pyjwt` (`jwt`)
   - Issues and verifies auth tokens used during voting.

## 4. How Android Communicates with Backend
All calls are HTTP to `API_BASE_URL` from [mobile/config.js](mobile/config.js).

### Registration
Endpoint: `POST /register`

Payload type: multipart/form-data
- `name`
- `aadhaar`
- `neutral`, `blink`, `smile`, `left`, `right` image files

App behavior:
1. Capture all expression frames.
2. Optimize images on device (resize/compress).
3. Upload multipart request.

Backend behavior:
1. Validates Aadhaar and registration state.
2. Processes uploaded images and computes encodings.
3. Stores encrypted average encoding + metadata.
4. Writes voter folder atomically (temp folder -> final folder).

### Registration Status Check
Endpoint: `GET /registration-status/{aadhaar}`

Used by app after timeout to confirm whether server actually completed registration.

### Authentication / Verification
Endpoint: `POST /authenticate`

Payload type: multipart/form-data
- `aadhaar`
- `image` (primary frame)
- `liveness_images` (multiple frames)

Backend behavior:
1. Loads registered encrypted encoding.
2. Compares primary frame with stored encoding.
3. Validates liveness frames against same identity and variation rules.
4. Returns JWT token when verification succeeds.

### Voting
Endpoint: `POST /vote`

Payload type: JSON + Bearer token
- header: `Authorization: Bearer <token>`
- body: `{ "candidate": "Candidate A|B|C|D" }`

Backend behavior:
1. Verifies token.
2. Ensures voter has not already voted.
3. Marks voter as voted and logs vote event.

## 5. What ML Models Are Used
This project uses pretrained face-recognition models through the `face_recognition` ecosystem.

Model usage in code:
1. Face detection and embedding creation happens in [server/main.py](server/main.py) inside:
   - `_compute_encoding_from_bytes(...)`
   - `face_recognition.face_locations(...)`
   - `face_recognition.face_encodings(...)`
2. No custom model training is performed in this repo.
3. Matching is done by embedding distance (Euclidean norm via NumPy).

So: ML is used for inference (recognition), not for training inside this project.

## 6. Security and Data Storage
Data folder: [database](database)

Per voter folder example: `database/<aadhaar>/`
- expression image files (`neutral.jpg`, `blink.jpg`, etc.)
- `encoding.enc` (encrypted embedding)
- `meta.json` (registration metadata + voted state)

Global files:
- `database/encodings.pkl` (index map)
- `database/audit_log.jsonl` (event log)
- `database/fernet.key` (persistent encryption key)

Important note:
- Keep `database/fernet.key` safe and persistent. If this key is changed/lost, old encrypted encodings become unreadable.

## 7. Liveness and Verification Logic
Liveness checks implemented in backend:
1. Minimum number of liveness frames.
2. Each liveness frame must match the registered face within threshold.
3. Inter-frame variation must exceed a minimum level to reduce static-photo spoofing.

Primary thresholds (from [server/main.py](server/main.py)):
- `FACE_MATCH_THRESHOLD`
- `LIVENESS_MATCH_THRESHOLD`
- `MIN_LIVENESS_FRAMES`
- `MIN_LIVENESS_VARIATION`

## 8. Practical Run Notes
Recommended backend run command (without auto-reload for stable registration):

```powershell
cd D:\Client\Biometric_voting_system
.\.venv\Scripts\python.exe -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Recommended app run command:

```powershell
cd D:\Client\Biometric_voting_system\mobile
npx expo start --dev-client --clear
```

Use a development build when native Expo modules are added/changed.
