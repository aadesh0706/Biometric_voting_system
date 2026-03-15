# 🗳️ Biometric Voting System

A secure multi-modal biometric voting system with face recognition, fingerprint verification, and continuous liveness detection.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [ toHow Use](#how-to-use)
- [Features](#features)
- [Project Structure](#project-structure)

---

## 🔧 Prerequisites

### System Requirements
- **Operating System:** Ubuntu 20.04+ / Windows 10+ / macOS
- **Python:** 3.8 or higher
- **Webcam:** Required for face capture
- **RAM:** 4GB minimum (8GB recommended)
- **Storage:** 2GB free space

### Required Software

#### 1. Install Python 3.8+
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Windows
# Download from https://www.python.org/downloads/
# Make sure to check "Add Python to PATH"
```

#### 2. Install CMake (required for dlib)
```bash
# Ubuntu/Debian
sudo apt install cmake

# Windows
# Download from https://cmake.org/download/
```

#### 3. Install Git
```bash
# Ubuntu/Debian
sudo apt install git

# Windows
# Download from https://git-scm.com/
```

---

## 🚀 Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/aadesh0706/Biometric_voting_system.git
cd Biometric_voting_system
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Ubuntu/Debian
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
# Install from requirements.txt
pip install -r requirements.txt

# If face-recognition fails, install dlib manually first:
# Ubuntu/Debian:
sudo apt install libcmake3 libboost-all-dev
pip install dlib
pip install face-recognition

# Windows:
# Download pre-built dlib wheel from:
# https://pypi.org/simple/dlib/
pip install dlib-19.22.99-cp38-cp38-win_amd64.whl
pip install face-recognition
```

### Step 4: Install Additional Required Packages
```bash
pip install streamlit opencv-python numpy pickle5 cryptography
```

---

## ▶️ Running the Project

### Start the Main Voting Application
```bash
# Make sure virtual environment is activated
streamlit run app.py
```

The application will open in your browser at: **http://localhost:8501**

### Running on Different Port
```bash
streamlit run app.py --server.port 8080
```

### For Development (Hot Reload)
```bash
streamlit run app.py --server.runOnSave true
```

---

## 📖 How to Use

### 1. Register as a New Voter

1. Open the application in browser
2. Select **"Register Voter"** from sidebar
3. Enter your **Full Name** and **Aadhaar Number** (12 digits)
4. Click **"Start Registration"**
5. Follow the camera instructions:
   - Keep a neutral face
   - Blink your eyes
   - Smile
   - Turn face left
   - Turn face right
6. Place your finger on the fingerprint scanner (if available)
7. Registration complete! ✅

### 2. Authenticate and Vote

1. Select **"Authenticate & Vote"** from sidebar
2. Enter your **Aadhaar Number**
3. Click **"Start Authentication"**
4. Look at the camera for face verification
5. Once authenticated, click **"Verify Liveness"**
6. Select your **candidate**
7. Click **"Submit Vote"**
8. Vote recorded securely! ✅

### 3. Admin Panel

1. Select **"Admin Panel"** from sidebar
2. View:
   - Registered voters list
   - Voting statistics
   - Activity logs

---

## ✨ Features

### 1. Registration ✅
- Aadhaar number verification
- Face capture with multiple expressions
- Fingerprint capture (optional)
- Duplicate prevention

### 2. Authentication ✅
- Face recognition verification
- Fingerprint matching
- Liveness detection

### 3. Continuous Liveness During Voting ✅
- Real-time face monitoring
- Presence detection
- Anti-spoofing protection

### 4. Voting ✅
- One vote per person
- Secure vote storage
- Voting log maintained

### 5. Database ✅
- SQLite database
- Encrypted sensitive data
- Voter status tracking

---

## 📁 Project Structure

```
Biometric_voting_system/
├── app.py                    # Main Streamlit application
├── api.py                    # Flask API (optional)
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── database/                # Voter data storage (auto-created)
│   ├── voters.db            # SQLite database
│   └── [aadhaar_folders]/  # Individual voter folders
└── encryption.key            # Encryption key (auto-created)
```

---

## 🔒 Security Notes

- All biometric data is encrypted using Fernet encryption
- Votes are stored anonymously in the database
- Each Aadhaar can only vote once
- Continuous liveness prevents impersonation

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'face_recognition'"
```bash
# Install dlib first, then face-recognition
pip install cmake
pip install dlib
pip install face-recognition
```

### Issue: "Camera not detected"
- Ensure webcam is connected and not in use by another app
- Check camera permissions in system settings

### Issue: "dlib installation fails"
```bash
# Ubuntu
sudo apt install cmake libboost-all-dev

# Or use conda
conda install -c conda-forge dlib
```

### Issue: "Port already in use"
```bash
# Use different port
streamlit run app.py --server.port 8502
```

---

## 📧 Support

For issues or questions, please create an issue on GitHub.

---

## 📄 License

MIT License
