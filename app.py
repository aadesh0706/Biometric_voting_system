import streamlit as st
import cv2
import os
import json
import numpy as np
import time
import face_recognition
import pickle
import shutil
import sqlite3
from datetime import datetime
from cryptography.fernet import Fernet
import hashlib
import base64

# ------------------------------
# Encryption Setup
# ------------------------------
KEY_FILE = "encryption.key"
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        cipher = Fernet(f.read())
else:
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    cipher = Fernet(key)

def encrypt_data(data):
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    return cipher.decrypt(encrypted_data.encode()).decode()

# ------------------------------
# Database Setup
# ------------------------------
DB_FILE = "voting.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS voters (
        aadhaar TEXT PRIMARY KEY,
        name TEXT,
        face_encoding BLOB,
        fingerprint_data TEXT,
        voted INTEGER DEFAULT 0,
        voted_at TEXT,
        registered_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aadhaar TEXT,
        candidate TEXT,
        voted_at TEXT,
        FOREIGN KEY(aadhaar) REFERENCES voters(aadhaar)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        details TEXT,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

def log_action(action, details):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO logs (action, details, timestamp) VALUES (?, ?, ?)", 
              (action, details, datetime.now().isoformat()))
    conn.commit()
    conn.close()

init_db()

# ------------------------------
# Base Folder Setup
# ------------------------------
BASE = "database"
os.makedirs(BASE, exist_ok=True)

st.set_page_config(page_title="Secure Voting System", layout="wide")
st.title("🗳️ Secure Biometric Voting System")

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        padding: 10px;
    }
    .success { color: green; }
    .error { color: red; }
</style>
""", unsafe_allow_html=True)

menu = ["Home", "Register Voter", "Authenticate & Vote", "Admin Panel"]
choice = st.sidebar.selectbox("Navigation", menu)

# ------------------------------
# Helper Functions
# ------------------------------
def generate_fingerprint_template():
    """Simulate fingerprint capture - in production, use DigitalPersona SDK"""
    # This is a placeholder - actual implementation requires DigitalPersona sensor
    # Returns a simulated fingerprint hash for demonstration
    return hashlib.sha256(str(time.time()).encode()).hexdigest()

def verify_fingerprint(live_template, stored_template):
    """Verify live fingerprint against stored template"""
    # Simplified verification - in production use proper biometric matching
    return live_template == stored_template

def check_liveness(frame):
    """Basic liveness detection using face detection"""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = face_recognition.face_locations(rgb)
    return len(faces) > 0

def continuous_liveness_check(session_duration=10):
    """Continuous liveness monitoring during voting"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "Camera not accessible"
    
    start_time = time.time()
    face_detected_count = 0
    total_frames = 0
    
    cv2.namedWindow("Liveness Check - Keep your face in frame", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Liveness Check - Keep your face in frame", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    while time.time() - start_time < session_duration:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)
        total_frames += 1
        
        # Check for face
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb)
        
        if len(faces) > 0:
            face_detected_count += 1
            status = "✓ Face Detected"
            color = (0, 255, 0)
        else:
            status = "⚠ No Face Detected!"
            color = (0, 0, 255)
        
        # Display info
        elapsed = int(time.time() - start_time)
        remaining = session_duration - elapsed
        cv2.putText(frame, f"Time: {remaining}s | {status}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, "Keep your face visible until verification complete", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("Liveness Check - Keep your face in frame", frame)
        
        if cv2.waitKey(1) & 0xFF == 27:
            cap.release()
            cv2.destroyAllWindows()
            return False, "Cancelled by user"
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Need at least 70% of frames with face detected
    if face_detected_count / total_frames < 0.7:
        return False, "Liveness check failed - insufficient face presence"
    
    return True, "Liveness verified"

# ------------------------------
# HOME PAGE
# ------------------------------
if choice == "Home":
    st.write("""
    ### 👋 Welcome to the Secure Biometric Voting System
    
    This system uses **multi-modal biometric authentication** including:
    - Face Recognition
    - Fingerprint Verification
    - Continuous Liveness Detection
    
    **Features:**
    - Secure voter registration with Aadhaar
    - Biometric authentication
    - One vote per person
    - Real-time liveness monitoring during voting
    - Encrypted database storage
    """)
    
    st.info("Please register first if you're a new voter!")

# ------------------------------
# REGISTER PAGE
# ------------------------------
elif choice == "Register Voter":
    st.header("📸 Voter Registration")
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name")
    with col2:
        aadhaar = st.text_input("Aadhaar Number (12 digits)", max_chars=12)
    
    st.markdown("### 📋 Registration Steps")
    st.write("1. Face capture (multiple expressions)")
    st.write("2. Fingerprint capture")
    st.write("3. Verification")
    
    if st.button("Start Registration"):
        if not name or len(aadhaar) != 12:
            st.error("Please enter valid Name and 12-digit Aadhaar number.")
        elif not aadhaar.isdigit():
            st.error("Aadhaar should contain only digits.")
        else:
            # Check for duplicate Aadhaar
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT aadhaar FROM voters WHERE aadhaar = ?", (aadhaar,))
            if c.fetchone():
                st.error("⚠️ This Aadhaar is already registered!")
                conn.close()
            else:
                conn.close()
                
                folder = os.path.join(BASE, aadhaar)
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                os.makedirs(folder)
                
                # Face capture with expressions
                expressions = [
                    ("neutral", "Keep a neutral face 😐"),
                    ("blink", "Blink your eyes 👀"),
                    ("smile", "Smile 😊"),
                    ("left", "Turn face LEFT ⬅️"),
                    ("right", "Turn face RIGHT ➡️")
                ]
                
                st.info("📷 Camera will open. Follow instructions and press ENTER for each capture.")
                
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    st.error("❌ Camera not detected.")
                else:
                    captured_images = {}
                    
                    for exp_name, instruction in expressions:
                        st.write(f"➡️ {instruction}")
                        print(f"[INFO] {instruction}")
                        
                        while True:
                            ret, frame = cap.read()
                            if not ret:
                                break
                            frame = cv2.flip(frame, 1)
                            text = f"{instruction} (Press ENTER)"
                            cv2.putText(frame, text, (20, 40),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                            cv2.imshow("Voter Registration", frame)
                            
                            key = cv2.waitKey(1)
                            if key == 13:  # ENTER
                                filename = os.path.join(folder, f"{exp_name}.jpg")
                                cv2.imwrite(filename, frame)
                                captured_images[exp_name] = filename
                                st.success(f"✅ Captured {exp_name}")
                                break
                            elif key == 27:  # ESC
                                cap.release()
                                cv2.destroyAllWindows()
                                shutil.rmtree(folder)
                                st.warning("Registration cancelled.")
                                st.stop()
                    
                    cap.release()
                    cv2.destroyAllWindows()
                    
                    # Process face encodings
                    encodings = []
                    for exp_name, img_path in captured_images.items():
                        img = face_recognition.load_image_file(img_path)
                        faces = face_recognition.face_encodings(img)
                        if faces:
                            encodings.append(faces[0])
                    
                    if not encodings:
                        st.error("❌ No faces detected. Please re-register.")
                        shutil.rmtree(folder)
                        st.stop()
                    
                    avg_encoding = np.mean(encodings, axis=0)
                    
                    # Check for duplicate face
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT face_encoding FROM voters")
                    duplicate_found = False
                    
                    for (stored_encoding,) in c.fetchall():
                        if stored_encoding:
                            stored = pickle.loads(stored_encoding)
                            distance = np.linalg.norm(avg_encoding - stored)
                            if distance <= 0.45:
                                duplicate_found = True
                                break
                    
                    if duplicate_found:
                        st.error("⚠️ Duplicate voter detected! Face already registered.")
                        shutil.rmtree(folder)
                        conn.close()
                    else:
                        # Capture fingerprint (simulated)
                        fingerprint_data = generate_fingerprint_template()
                        
                        # Store in encrypted database
                        encoded_face = pickle.dumps(avg_encoding)
                        c.execute("INSERT INTO voters (aadhaar, name, face_encoding, fingerprint_data, voted, registered_at) VALUES (?, ?, ?, ?, ?, ?)",
                                 (aadhaar, name, encoded_face, encrypt_data(fingerprint_data), 0, datetime.now().isoformat()))
                        conn.commit()
                        conn.close()
                        
                        log_action("REGISTRATION", f"Voter registered: {aadhaar}")
                        
                        st.success(f"🎉 Registration Completed for {name}!")
                        st.balloons()
                        st.info(f"Aadhaar: {aadhaar}")
                        st.info("You can now authenticate and vote!")

# ------------------------------
# AUTHENTICATION + VOTING
# ------------------------------
elif choice == "Authenticate & Vote":
    st.header("🗳️ Authentication & Voting")
    
    aadhaar = st.text_input("Enter Aadhaar Number (12 digits)", key="aadhaar_input")
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "voting_done" not in st.session_state:
        st.session_state.voting_done = False
    if "voter_name" not in st.session_state:
        st.session_state.voter_name = ""
    
    # Step 1: Authentication
    if not st.session_state.authenticated:
        if st.button("Start Authentication"):
            if len(aadhaar) != 12 or not aadhaar.isdigit():
                st.error("Please enter a valid 12-digit Aadhaar number.")
            else:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT name, face_encoding, voted FROM voters WHERE aadhaar = ?", (aadhaar,))
                result = c.fetchone()
                conn.close()
                
                if not result:
                    st.error("❌ No registration found for this Aadhaar.")
                else:
                    voter_name, face_encoding, voted = result
                    
                    if voted:
                        st.warning("⚠️ This Aadhaar has already voted!")
                        st.stop()
                    
                    known_encoding = pickle.loads(face_encoding)
                    
                    st.info("📷 Camera will open. Press ENTER to capture for authentication.")
                    
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        st.error("❌ Unable to access camera.")
                    else:
                        verified = False
                        
                        while True:
                            ret, frame = cap.read()
                            if not ret:
                                continue
                            frame = cv2.flip(frame, 1)
                            cv2.putText(frame, "Align face & Press ENTER (ESC to cancel)", (20, 40),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            cv2.imshow("Authenticate Voter", frame)
                            
                            key = cv2.waitKey(1)
                            if key == 13:  # ENTER
                                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                encodings = face_recognition.face_encodings(rgb)
                                
                                if encodings:
                                    distance = np.linalg.norm(encodings[0] - known_encoding)
                                    if distance < 0.45:
                                        verified = True
                                        st.success(f"✅ Authentication Successful! Welcome {voter_name}")
                                        log_action("AUTH_SUCCESS", f"Voter authenticated: {aadhaar}")
                                    else:
                                        st.error("❌ Face not recognized.")
                                else:
                                    st.error("❌ No face detected.")
                                break
                            elif key == 27:  # ESC
                                st.warning("Authentication cancelled.")
                                break
                        
                        cap.release()
                        cv2.destroyAllWindows()
                        
                        if verified:
                            st.session_state.authenticated = True
                            st.session_state.voter_name = voter_name
                            st.rerun()
    
    # Step 2: Voting
    elif st.session_state.authenticated and not st.session_state.voting_done:
        st.subheader(f"🗳️ Voting Portal - Welcome, {st.session_state.voter_name}!")
        
        # Continuous liveness check
        st.info("🔒 Continuous liveness verification required for voting...")
        
        if st.button("Verify Liveness & Start Voting"):
            with st.spinner("Verifying... Keep your face visible..."):
                liveness_ok, message = continuous_liveness_check(session_duration=5)
            
            if liveness_ok:
                st.success("✅ Liveness verified! You may now cast your vote.")
                
                candidates = ["Candidate A", "Candidate B", "Candidate C", "Candidate D"]
                selected = st.radio("Select your candidate:", candidates, key="vote_choice")
                
                if st.button("Submit Vote"):
                    if selected:
                        # Record vote
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("UPDATE voters SET voted = 1, voted_at = ? WHERE aadhaar = ?",
                                 (datetime.now().isoformat(), aadhaar))
                        c.execute("INSERT INTO votes (aadhaar, candidate, voted_at) VALUES (?, ?, ?)",
                                 (aadhaar, selected, datetime.now().isoformat()))
                        conn.commit()
                        conn.close()
                        
                        log_action("VOTE_CAST", f"Vote cast by: {aadhaar}")
                        
                        st.session_state.voting_done = True
                        st.balloons()
                        st.success("🎉 Thank you for voting! Your vote has been recorded securely.")
                        st.rerun()
                    else:
                        st.warning("Please select a candidate.")
            else:
                st.error(f"❌ Liveness check failed: {message}")
                log_action("LIVENESS_FAIL", f"Failed for: {aadhaar}")
    
    # Step 3: After voting
    elif st.session_state.voting_done:
        st.success("🎉 You have already submitted your vote!")
        if st.button("Start New Authentication"):
            st.session_state.authenticated = False
            st.session_state.voting_done = False
            st.rerun()

# ------------------------------
# ADMIN PANEL
# ------------------------------
elif choice == "Admin Panel":
    st.header("👨‍💻 Admin Panel")
    
    # View registered voters
    st.subheader("📊 Registered Voters")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT aadhaar, name, voted, registered_at FROM voters ORDER BY registered_at DESC")
    voters = c.fetchall()
    
    if voters:
        for v in voters:
            aadhaar, name, voted, registered = v
            status = "✅ Voted" if voted else "⏳ Not Voted"
            st.write(f"**{name}** | Aadhaar: {aadhaar[:4]}****{aadhaar[-4:]} | {status}")
    else:
        st.info("No voters registered yet.")
    
    st.subheader("📈 Voting Statistics")
    c.execute("SELECT COUNT(*) FROM voters")
    total_voters = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM voters WHERE voted = 1")
    total_voted = c.fetchone()[0]
    
    col1, col2 = st.columns(2)
    col1.metric("Total Registered", total_voters)
    col2.metric("Total Voted", total_voted)
    
    st.subheader("📝 Recent Logs")
    c.execute("SELECT action, details, timestamp FROM logs ORDER BY timestamp DESC LIMIT 10")
    logs = c.fetchall()
    for log in logs:
        st.write(f"**{log[0]}**: {log[1]} - {log[2]}")
    
    conn.close()
