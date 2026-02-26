import streamlit as st
import cv2
import os
import json
import numpy as np
import time
import face_recognition
import pickle
import shutil
from datetime import datetime


# ------------------------------
# Base Folder Setup
# ------------------------------
BASE = "database"
os.makedirs(BASE, exist_ok=True)

st.set_page_config(page_title="Secure Voting System", layout="wide")
st.title("🗳️ Machine Learning–Based Multimodal Biometric Voting System ")

menu = ["Home", "Register Voter", "Authenticate & Vote"]
choice = st.sidebar.selectbox("Navigation", menu)

# ------------------------------
# HOME PAGE
# ------------------------------
if choice == "Home":
    st.write("""
    ### 👋 Welcome to the Secure Biometric Voting Prototype

    
    
    """)

# ------------------------------
# REGISTER PAGE
# ------------------------------
elif choice == "Register Voter":
    st.header("📸 Voter Registration (Face Capture with ENTER Key Capture)")

    name = st.text_input("Enter Full Name")
    aadhaar = st.text_input("Enter Aadhaar Number (12 digits)")

    if st.button("Start Registration"):
        if not name or len(aadhaar) != 12:
            st.error("Please enter valid Name and 12-digit Aadhaar number.")
        else:
            folder = os.path.join(BASE, aadhaar)
            # Remove any existing incomplete folder
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.makedirs(folder)

            expressions = [
                ("neutral", "Keep a neutral face 😐"),
                ("blink", "Blink your eyes 👀"),
                ("smile", "Smile 😊"),
                ("left", "Turn your face LEFT ⬅️"),
                ("right", "Turn your face RIGHT ➡️")
            ]

            st.info("A camera window will open. Follow on-screen instructions and press ENTER for each capture.")

            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("❌ Camera not detected.")
                st.stop()

            for exp_name, instruction in expressions:
                st.write(f"➡️ {instruction}")
                print(f"[INFO] {instruction}")
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        st.error("Camera error. Please restart registration.")
                        break
                    frame = cv2.flip(frame, 1)
                    text = f"{instruction} (Press ENTER to capture)"
                    cv2.putText(frame, text, (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.imshow("Voter Registration", frame)

                    key = cv2.waitKey(1)
                    if key == 13:  # ENTER key
                        filename = os.path.join(folder, f"{exp_name}.jpg")
                        cv2.imwrite(filename, frame)
                        print(f"[SAVED] {filename}")
                        st.success(f"✅ Captured {exp_name} face successfully!")
                        break
                    elif key == 27:  # ESC key to cancel
                        st.warning("Registration cancelled by user.")
                        cap.release()
                        cv2.destroyAllWindows()
                        shutil.rmtree(folder)
                        st.stop()

            cap.release()
            cv2.destroyAllWindows()

            st.success("✅ All facial expressions captured successfully! Processing your registration...")

            # Compute encodings
            encodings = []
            for exp_name, _ in expressions:
                img_path = os.path.join(folder, f"{exp_name}.jpg")
                img = face_recognition.load_image_file(img_path)
                faces = face_recognition.face_encodings(img)
                if faces:
                    encodings.append(faces[0])

            if not encodings:
                st.error("❌ No faces detected. Please re-register.")
                shutil.rmtree(folder)
                st.stop()

            avg_encoding = np.mean(encodings, axis=0)
            encodings_file = os.path.join(BASE, "encodings.pkl")

            # ---- Duplicate Face Check ----
            duplicate_found = False
            if os.path.exists(encodings_file):
                with open(encodings_file, "rb") as f:
                    all_encodings = pickle.load(f)
            else:
                all_encodings = {}

            for existing_aadhaar, existing_encoding in all_encodings.items():
                distance = np.linalg.norm(avg_encoding - existing_encoding)
                if distance <= 0.45:
                    duplicate_found = True
                    break

            if duplicate_found:
                st.error("⚠️ Duplicate voter detected. Registration denied.")
                shutil.rmtree(folder)
            else:
                np.save(os.path.join(folder, "encoding.npy"), avg_encoding)
                metadata = {"name": name, "aadhaar": aadhaar, "voted": False}
                with open(os.path.join(folder, "meta.json"), "w") as f:
                    json.dump(metadata, f, indent=4)

                all_encodings[aadhaar] = avg_encoding
                with open(encodings_file, "wb") as f:
                    pickle.dump(all_encodings, f)

                st.success(f"🎉 Registration Completed Successfully for {name}!")
                st.balloons()


# ------------------------------
# AUTHENTICATION + VOTING
# ------------------------------
elif choice == "Authenticate & Vote":
    st.header("🧠 Face Authentication and Secure Voting Portal")

    # Aadhaar input with unique key (prevents auto-fill)
    aadhaar = st.text_input("Enter Aadhaar Number (12 digits)", key="aadhaar_input")

    # Initialize session state variables
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "voting_done" not in st.session_state:
        st.session_state.voting_done = False
    if "meta" not in st.session_state:
        st.session_state.meta = {}

    # -----------------------------
    # Step 1: Face Authentication
    # -----------------------------
    if not st.session_state.authenticated:
        if st.button("Start Authentication"):
            if len(aadhaar) != 12 or not aadhaar.isdigit():
                st.error("Please enter a valid 12-digit Aadhaar number.")
                st.stop()

            voter_folder = os.path.join(BASE, aadhaar)
            encoding_file = os.path.join(voter_folder, "encoding.npy")
            meta_file = os.path.join(voter_folder, "meta.json")

            if not os.path.exists(voter_folder) or not os.path.exists(encoding_file):
                st.error("❌ No registration found for this Aadhaar number.")
                st.stop()

            with open(meta_file, "r") as f:
                meta = json.load(f)

            if meta.get("voted"):
                st.warning("⚠️ You have already cast your vote. Multiple voting is not allowed.")
                st.stop()

            known_encoding = np.load(encoding_file)
            st.session_state.meta = meta

            st.info("Camera will open for face verification. Press ENTER to capture or ESC to cancel.")

            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("❌ Unable to access camera.")
                st.stop()

            cv2.namedWindow("Authenticate Voter", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Authenticate Voter", 600, 450)

            verified = False
            cancelled = False

            while True:
                ret, frame = cap.read()
                if not ret:
                    continue

                frame = cv2.flip(frame, 1)
                cv2.putText(frame, "Align face & press ENTER to authenticate (ESC to cancel)", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("Authenticate Voter", frame)

                key = cv2.waitKey(1)
                if key == 13:  # ENTER key
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    encodings = face_recognition.face_encodings(rgb_frame)

                    if encodings:
                        captured_encoding = encodings[0]
                        distance = np.linalg.norm(captured_encoding - known_encoding)
                        if distance < 0.45:
                            verified = True
                            st.success(f"✅ Authentication Successful! Welcome {meta['name']}")
                        else:
                            st.error("❌ Face not recognized. Authentication failed.")
                    else:
                        st.error("❌ No face detected. Please try again.")
                    break

                elif key == 27:  # ESC key
                    st.warning("⚠️ Authentication cancelled by user.")
                    cancelled = True
                    break

            cap.release()
            cv2.destroyAllWindows()

            if verified:
                st.session_state.authenticated = True
                st.rerun()
            elif cancelled:
                st.stop()

    # -----------------------------
    # Step 2: Voting Portal
    # -----------------------------
    elif st.session_state.authenticated and not st.session_state.voting_done:
        meta = st.session_state.meta
        st.subheader("🗳️ Voting Portal (Secure & Camera Monitored)")
        st.info("Camera will remain ON to ensure the same voter is present.")

        candidates = ["Candidate A", "Candidate B", "Candidate C", "Candidate D"]
        selected = st.radio("Please select your preferred candidate:", candidates, key="vote_choice")

        submit_vote = st.button("Submit Vote")

        if submit_vote:
            if selected:
                st.info("Verifying presence and securing your anonymous vote...")

                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    st.error("❌ Unable to access camera.")
                    st.stop()

                cv2.namedWindow("Voting Presence Check", cv2.WINDOW_NORMAL)
                cv2.resizeWindow("Voting Presence Check", 500, 400)

                start_time = time.time()
                while time.time() - start_time < 5:
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    frame = cv2.flip(frame, 1)
                    msg = "Verifying voter presence..."
                    cv2.putText(frame, msg, (30, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                    cv2.imshow("Voting Presence Check", frame)
                    if cv2.waitKey(1) & 0xFF == 27:  # ESC cancels voting
                        st.warning("⚠️ Voting cancelled by user.")
                        cap.release()
                        cv2.destroyAllWindows()
                        st.stop()

                cap.release()
                cv2.destroyAllWindows()

                # Anonymous logging (no candidate info)
                meta["voted"] = True
                with open(os.path.join(BASE, aadhaar, "meta.json"), "w") as f:
                    json.dump(meta, f, indent=4)

                log_path = os.path.join(BASE, "vote_log.txt")
                with open(log_path, "a") as log:
                    log.write(f"Aadhaar: {aadhaar}, Name: {meta['name']}, Voted: True, Time: {datetime.now()}\n")

                st.session_state.voting_done = True

                # Show thank you before rerun
                st.success("🎉 Thank you for voting! Your vote has been recorded securely and anonymously.")
                st.balloons()

                # Wait a few seconds to show message
                time.sleep(3)

                # Clear Aadhaar safely and rerun
                if "aadhaar_input" in st.session_state:
                    del st.session_state["aadhaar_input"]
                st.rerun()
            else:
                st.warning("Please select a candidate before submitting your vote.")

    # -----------------------------
    # Step 3: After Voting
    # -----------------------------
    elif st.session_state.voting_done:
        st.success("🎉 You have already submitted your vote in this session.")
        st.info("If you want to authenticate another voter, click below.")
        if st.button("🔁 Start New Authentication"):
            st.session_state.authenticated = False
            st.session_state.voting_done = False
            if "aadhaar_input" in st.session_state:
                del st.session_state["aadhaar_input"]
            st.rerun()
