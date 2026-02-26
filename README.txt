================================================================================
                    BIOMETRIC VOTING SYSTEM - PROJECT DOCUMENTATION
================================================================================

PROJECT OVERVIEW
----------------
This is a secure biometric voting system that uses Android fingerprint 
authentication for voter registration, authentication, and vote casting. 
The system consists of a React Native mobile application and a Python 
FastAPI backend server.

TECHNOLOGIES USED
-----------------

Mobile Application:
* React Native - Cross-platform mobile framework
* Expo SDK 50.0.0 - Development and build tooling
* expo-local-authentication - Android fingerprint sensor integration
* AsyncStorage - Local data caching on mobile device
* JavaScript/React - Programming language and UI framework

Backend Server:
* Python 3.8+ - Programming language
* FastAPI - Modern web framework for building APIs
* Uvicorn - ASGI server for running FastAPI
* Pydantic - Data validation and settings management
* JSON - Data storage format (votes.json, voters.json)

Build Tools (Android):
* Gradle 8.3 - Build automation tool
* Java 17 (Eclipse Adoptium) - Required for Android compilation
* Android SDK 34 - Android platform tools
* Android NDK 25.1.8937393 - Native development kit
* ADB (Android Debug Bridge) - Device communication and app installation

SYSTEM ARCHITECTURE
-------------------

The system has three main components:

1. Mobile App (Frontend)
   - Provides user interface for voters
   - Captures fingerprint biometric data using device hardware
   - Communicates with backend API via HTTP requests
   - Stores voter session data locally using AsyncStorage

2. Backend API (Server)
   - Validates voter Aadhaar numbers and names
   - Tracks voting status (who has voted)
   - Records anonymous votes for each candidate
   - Serves vote tallies and statistics

3. Android Device
   - Physical fingerprint sensor for biometric authentication
   - Secure enclave for biometric data storage
   - Network connectivity to reach backend server

HOW THE SYSTEM WORKS
--------------------

VOTER REGISTRATION FLOW:
1. Voter opens the mobile app on Android device
2. Enters Aadhaar number (12-digit unique ID) and full name
3. App prompts for fingerprint scan using Android biometric prompt
4. Upon successful fingerprint authentication:
   - App sends registration request to backend API
   - Backend validates Aadhaar format and checks for duplicates
   - Backend creates voter record in voters.json
   - App caches voter data locally in AsyncStorage
5. Registration success message displayed

VOTER AUTHENTICATION FLOW:
1. Voter selects "Authenticate" option in app
2. Enters registered Aadhaar number
3. App prompts for fingerprint scan
4. Upon successful fingerprint authentication:
   - App sends authentication request to backend
   - Backend checks if voter is registered
   - Backend verifies voter has not already voted
   - Backend returns voting eligibility status
5. App displays whether voter can proceed to vote

VOTING FLOW:
1. Voter selects "Vote" option
2. Enters Aadhaar number
3. App prompts for fingerprint scan
4. Upon successful fingerprint authentication:
   - App retrieves voter data from backend
   - Backend confirms voter is eligible (registered and not voted)
   - App displays list of candidates
5. Voter selects preferred candidate
6. App prompts for fingerprint confirmation scan
7. Upon confirmation:
   - App sends vote to backend (Aadhaar + candidate)
   - Backend records anonymous vote in votes.json
   - Backend marks voter as "has_voted" in voters.json
   - Backend prevents duplicate voting
8. Vote confirmation displayed to voter

SECURITY FEATURES
-----------------

Biometric Security:
* Fingerprint data never leaves the Android device
* Android Secure Hardware stores biometric templates
* expo-local-authentication uses Android BiometricPrompt API
* Fingerprint verification happens in device's Trusted Execution Environment

Vote Anonymity:
* Backend separates voter identity from vote choice
* votes.json only stores: {candidate: name, timestamp: time}
* No link between Aadhaar number and candidate selection
* Voting status tracked separately without revealing vote choice

Duplicate Prevention:
* Each Aadhaar can register only once
* Backend checks "has_voted" flag before accepting votes
* Atomic write operations prevent race conditions

Network Security:
* All API communications use HTTP (can be upgraded to HTTPS)
* IP-based access control (currently local network: 10.215.151.85)
* Request validation using Pydantic models

PROJECT STRUCTURE
-----------------

Biometric_voting_system/
|
|-- mobile/                          (React Native Android App)
|   |-- App.js                       (Main application component)
|   |-- config.js                    (Configuration: API URL, candidates)
|   |-- package.json                 (NPM dependencies)
|   |-- app.json                     (Expo configuration)
|   |-- android/                     (Native Android build files)
|       |-- build.gradle             (Gradle build configuration)
|       |-- gradle.properties        (Gradle and Java settings)
|       |-- app/src/main/res/        (Android resources)
|
|-- api.py                           (FastAPI backend server)
|-- requirements.txt                 (Python dependencies for backend)
|-- votes.json                       (Anonymous vote records)
|-- voters.json                      (Voter registration database)
|-- admin/                           (Web admin interface - optional)

CONFIGURATION FILES
-------------------

mobile/config.js:
* API_BASE_URL: Backend server address (http://10.215.151.85:8000)
* CANDIDATES: List of candidates [{id, name, party}]
* FINGERPRINT_PROMPT_MESSAGES: Biometric prompt customization

mobile/android/gradle.properties:
* org.gradle.java.home: Path to Java 17 installation
* newArchEnabled: React Native architecture (false = old arch)
* hermesEnabled: JavaScript engine (true = Hermes)

api.py configuration:
* CORS origins: Allowed client origins (currently "*" for development)
* Data files: votes.json and voters.json locations

NETWORK SETUP
-------------

Current Configuration:
* Backend Server IP: 10.215.151.85
* Backend Server Port: 8000
* API Base URL: http://10.215.151.85:8000

Requirements:
* Both Android device and server must be on same local network
* Windows Firewall must allow incoming connections on port 8000
* Network should allow device-to-PC communication

To Find Your IP Address:
* Open PowerShell
* Run: ipconfig
* Look for "IPv4 Address" under your active network adapter
* Update mobile/config.js with new IP if network changes

INSTALLATION AND SETUP
----------------------

PREREQUISITES:
* Node.js 16+ and NPM installed
* Python 3.8+ installed
* Java 17 (Eclipse Adoptium) installed
* Android SDK installed
* Android device with fingerprint sensor
* USB cable for ADB connection

BACKEND SETUP:

1. Install Python dependencies:
   cd d:\Client\Biometric_voting_system
   pip install fastapi uvicorn pydantic python-multipart

2. Start the backend server:
   python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

3. Verify server is running:
   Open browser: http://localhost:8000
   Should see: {"message":"Biometric Voting API - Fingerprint Authentication"}

MOBILE APP SETUP:

1. Install Node dependencies:
   cd d:\Client\Biometric_voting_system\mobile
   npm install

2. Update network configuration:
   Edit mobile/config.js
   Change API_BASE_URL to your PC's IP address

3. Connect Android device via USB:
   Enable USB Debugging in Developer Options
   Run: adb devices
   Device should appear in list

4. Build and install app:
   Set environment variables:
   $env:JAVA_HOME="C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot"
   $env:ANDROID_HOME="D:\Android\android-sdk"
   
   Build and run:
   npx expo run:android --device

5. App will install and launch on your Android device

RUNNING THE APPLICATION
------------------------

STARTING THE BACKEND:
cd d:\Client\Biometric_voting_system
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

The server will run on: http://10.215.151.85:8000
Keep this terminal window open while using the app.

USING THE MOBILE APP:

1. Launch "Biometric Voting" app on Android device

2. REGISTER A NEW VOTER:
   - Tap "Register New Voter" button
   - Enter 12-digit Aadhaar number
   - Enter full name
   - Tap "Register" button
   - Scan fingerprint when prompted
   - Wait for success confirmation

3. AUTHENTICATE (Check Voting Status):
   - Tap "Authenticate Voter" button
   - Enter registered Aadhaar number
   - Tap "Authenticate" button
   - Scan fingerprint when prompted
   - View voting eligibility status

4. CAST A VOTE:
   - Tap "Cast Vote" button
   - Enter registered Aadhaar number
   - Tap "Authenticate to Vote" button
   - Scan fingerprint when prompted
   - Select your preferred candidate
   - Confirm selection
   - Scan fingerprint again to confirm vote
   - Vote recorded successfully

API ENDPOINTS
-------------

GET /
Description: Health check endpoint
Response: {"message":"Biometric Voting API - Fingerprint Authentication"}

POST /register
Description: Register a new voter
Request Body: {
  "aadhaar": "123456789012",
  "name": "Voter Full Name"
}
Response: {
  "success": true,
  "message": "Voter registered successfully"
}

POST /authenticate
Description: Check voter eligibility
Request Body: {
  "aadhaar": "123456789012"
}
Response: {
  "success": true,
  "can_vote": true/false,
  "message": "Status message",
  "voter_name": "Name"
}

POST /vote
Description: Cast an anonymous vote
Request Body: {
  "aadhaar": "123456789012",
  "candidate": "Candidate Name"
}
Response: {
  "success": true,
  "message": "Vote recorded successfully"
}

GET /results
Description: Get current vote tallies
Response: {
  "total_votes": 10,
  "results": {
    "Candidate A": 5,
    "Candidate B": 3,
    "Candidate C": 2
  }
}

DATA STORAGE
------------

voters.json Format:
[
  {
    "aadhaar": "123456789012",
    "name": "Voter Name",
    "has_voted": false,
    "registered_at": "2026-02-18T10:30:00"
  }
]

votes.json Format:
[
  {
    "candidate": "Candidate Name",
    "timestamp": "2026-02-18T11:45:00"
  }
]

AsyncStorage (Mobile Device):
Key: voter_data
Value: {
  "aadhaar": "123456789012",
  "name": "Voter Name"
}

TROUBLESHOOTING
---------------

MOBILE APP ISSUES:

Problem: "Cannot connect to server"
Solution: 
- Check backend server is running
- Verify IP address in mobile/config.js matches server
- Ensure device and PC are on same network
- Check Windows Firewall allows port 8000

Problem: Fingerprint not working
Solution:
- Ensure device has fingerprint sensor
- At least one fingerprint must be enrolled in device settings
- App must have biometric permission (granted at install)
- Try re-registering fingerprint in Android Settings

Problem: "Module not found" errors
Solution:
- Delete node_modules folder
- Run: npm install
- Clear cache: npx expo start --clear

BUILD ISSUES:

Problem: "Unsupported class file major version"
Solution:
- Install Java 17 (not Java 25 or older versions)
- Set JAVA_HOME to Java 17 installation path
- Update android/gradle.properties with correct Java path

Problem: "SDK licenses not accepted"
Solution:
- Create license acceptance file manually
- Or update Android SDK and accept licenses

Problem: Gradle build fails
Solution:
- Clean build: Remove android/.gradle and android/app/build
- Ensure Gradle 8.3 is configured
- Check Java 17 is being used

BACKEND ISSUES:

Problem: "Module not found" errors
Solution:
- Install all requirements: pip install -r requirements.txt
- Verify Python 3.8+ is installed

Problem: Port 8000 already in use
Solution:
- Kill existing process: Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
- Or use different port: --port 8001

CANDIDATES CONFIGURATION
------------------------

To add or modify candidates, edit mobile/config.js:

export const CANDIDATES = [
  { id: 1, name: 'Candidate Name', party: 'Party Name' },
  { id: 2, name: 'Another Candidate', party: 'Another Party' },
  // Add more candidates here
];

After modifying:
1. Save the file
2. Rebuild the app: npx expo run:android --device
3. Or use Metro bundler hot reload if running in dev mode

SYSTEM REQUIREMENTS
-------------------

Server Machine (Windows PC):
* Windows 10/11
* Python 3.8 or higher
* Port 8000 available
* Network connectivity

Android Device:
* Android 6.0 (Marshmallow) or higher
* Fingerprint sensor hardware
* At least one fingerprint enrolled
* USB debugging enabled
* 100MB free storage space

Development Machine:
* Node.js 16+
* Java 17 (Eclipse Adoptium JDK)
* Android SDK with Build Tools 34.0.0
* ADB (Android Debug Bridge)
* 2GB free disk space for build artifacts

KNOWN LIMITATIONS
-----------------

* Fingerprint data security depends on Android device security
* No HTTPS encryption (development only)
* File-based storage (not suitable for large-scale production)
* No admin panel for managing voters/votes
* Single backend instance (no load balancing)
* IP address must be updated when network changes
* Requires USB connection for initial app installation

FUTURE ENHANCEMENTS
-------------------

* Web admin dashboard for election management
* HTTPS/SSL encryption for API communications
* Database backend (PostgreSQL/MySQL) instead of JSON files
* Multi-factor authentication (Fingerprint + OTP)
* Face recognition as alternative biometric
* Offline voting capability with sync
* Vote encryption end-to-end
* Real-time vote counting dashboard
* Voter registration approval workflow
* Election scheduling and management

TECHNICAL NOTES
---------------

Expo SDK Version: 50.0.0
React Native Version: 0.73.6
Gradle Version: 8.3
Java Version: 17.0.18.8 (Eclipse Adoptium)
Android Compile SDK: 34
Android Min SDK: 21 (Android 5.0)
Android Target SDK: 34

Important Dependencies:
* expo-local-authentication: 13.8.0
* @react-native-async-storage/async-storage: 1.21.0
* fastapi: 0.110.0+
* uvicorn: 0.27.0+

Metro Bundler Port: 8081
Expo Dev Client: Enabled

APP PACKAGE DETAILS
-------------------

Package Name: com.anonymous.biometricvotingmobile
App Name: Biometric Voting
Version: 1.0.0
Bundle Identifier: com.anonymous.biometricvotingmobile

Permissions Required:
* USE_BIOMETRIC - Fingerprint sensor access
* USE_FINGERPRINT - Legacy fingerprint API
* INTERNET - Network communication

DEVELOPMENT WORKFLOW
--------------------

1. Make code changes in App.js or config.js
2. Backend changes in api.py
3. Metro bundler auto-reloads (if running in dev mode)
4. For native changes, rebuild: npx expo run:android --device
5. Test on physical device with registered fingerprints
6. Check backend logs for API request/response details

SUPPORT AND CONTACT
-------------------

For technical issues or questions:
* Check troubleshooting section above
* Review error messages in terminal output
* Verify all prerequisites are installed correctly
* Ensure network connectivity between device and server

PROJECT STATUS: Fully Functional
Last Updated: February 18, 2026
Build Status: Successfully deployed on Android via ADB

================================================================================
                              END OF DOCUMENTATION
================================================================================
