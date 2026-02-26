# 🔧 Android ADB Setup - Fix Java Version Issue

## ⚠️ Problem
Your Java version (25.0.2) is too new for React Native/Expo build tools.
Gradle needs Java 17 LTS.

---

## ✅ SOLUTION 1: Use Expo Go (Recommended - Fastest)

### Step 1: Install Expo Go on Your Phone
**Option A - Google Play Store (Easiest):**
1. Open Google Play Store on your phone
2. Search for "Expo Go"
3. Install the app

**Option B - Via ADB:**
```powershell
# Download Expo Go APK from official source
# You can get it from: https://expo.dev/go

# Then install via ADB:
D:\Android\android-sdk\platform-tools\adb.exe install path\to\expo-go.apk
```

### Step 2: Start Expo with Device Connection
```powershell
cd D:\Client\Biometric_voting_system\mobile

# Option 1: Auto-connect via ADB
npx expo start --android

# Option 2: Manual connection  
npx expo start --lan
```

### Step 3: App Opens Automatically
The app will open in Expo Go on your connected device!

---

## ✅ SOLUTION 2: Build Native APK (Requires Java 17)

If you want a standalone APK without Expo Go:

### Step 1: Install Java 17 LTS
1. Download Java 17 from: https://adoptium.net/temurin/releases/?version=17
   - Select: **Windows x64 JDK .msi installer**
   - Version: **17 LTS**

2. Install and note the installation path (e.g., `C:\Program Files\Eclipse Adoptium\jdk-17.0.x`)

### Step 2: Set JAVA_HOME for Current Session
```powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.x"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
```

### Step 3: Verify Java Version
```powershell
java -version
# Should show: openjdk version "17.0.x"
```

### Step 4: Build and Install APK
```powershell
cd D:\Client\Biometric_voting_system\mobile

# Clean previous build
Remove-Item -Recurse -Force android\app\build -ErrorAction SilentlyContinue

# Build and install
npx expo run:android
```

---

## 🚀 Quick Start (Recommended)

**Backend is already running at: http://10.215.151.85:8000**

Just run this:
```powershell
cd D:\Client\Biometric_voting_system\mobile
npx expo start --android
```

This will:
1. ✅ Start Expo dev server
2. ✅ Connect to your ADB device automatically  
3. ✅ Open app in Expo Go (if installed)
4. ✅ Hot reload on code changes

---

## 📱 Current Configuration

- **IP Address:** 10.215.151.85 (Updated in config.js)
- **Backend:** http://10.215.151.85:8000 (Running)
- **Device:** 10BE1M0DT4000H9 (Connected via ADB)
- **Package:** com.anonymous.biometricvotingmobile

---

## 🐛 Troubleshooting

**"Expo Go not installed":**
- Install from Play Store or use Solution 2

**"Port 8000 not responding":**
```powershell
# Restart backend
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**"Device not found":**
```powershell
D:\Android\android-sdk\platform-tools\adb.exe devices
# Should show: 10BE1M0DT4000H9 device
```

---

## ⚡ Next Steps

1. Install Expo Go on your phone (from Play Store)
2. Run: `cd mobile` then `npx expo start --android`
3. App opens automatically on your device!

Done! 🎉
