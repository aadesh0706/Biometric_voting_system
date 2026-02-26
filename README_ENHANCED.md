# Biometric Voting System - Enhanced with Fingerprint & Liveness Detection

## Installation

```bash
# Install required packages
pip install -r requirements.txt

# Install additional packages for fingerprint and encryption
pip install opencv-python numpy pickle5 face-recognition pycryptodome sqlalchemy flask
```

## Running the System

```bash
# Start the main voting application
streamlit run app.py

# Start the API server (optional - for mobile integration)
python api.py
```

## Features

### 1. Registration
- ✅ Capture Aadhaar number and voter name
- ✅ Capture face image using webcam (multiple expressions)
- ✅ Capture fingerprint using DigitalPersona sensor
- ✅ Extract and store biometric features securely
- ✅ Prevent duplicate registration (face + Aadhaar)

### 2. Authentication
- ✅ Verify Aadhaar number
- ✅ Match live face with stored face data
- ✅ Match live fingerprint with stored fingerprint data
- ✅ Basic liveness check (blink detection)
- ✅ Allow access only if authentication is successful

### 3. Continuous Liveness During Voting
- ✅ Turn ON camera during voting session
- ✅ Continuously monitor voter's face
- ✅ Ensure the same real person remains present
- ✅ Detect face disappearance or replacement
- ✅ Cancel session if liveness fails
- ✅ Prevent vote submission if identity is lost

### 4. Voting
- ✅ Allow voter to cast vote only once
- ✅ Lock voter after vote submission
- ✅ Store vote securely
- ✅ Maintain voting log

### 5. Database
- ✅ Store voter and vote data securely (SQLite)
- ✅ Maintain voter status (Voted / Not Voted)
- ✅ Encrypt sensitive information

## Hardware Requirements
- Webcam (for face capture)
- DigitalPersona U.are.U fingerprint reader (optional)
