# 📱 Biometric Voting System - Android Mobile App

A secure fingerprint-based voting system for Android devices using React Native (Expo) and FastAPI.

## 🎯 Features

- ✅ **Fingerprint Authentication** - Uses Android's native fingerprint sensor
- ✅ **Voter Registration** - Register with Aadhaar number and fingerprint
- ✅ **Secure Login** - Authenticate using fingerprint
- ✅ **One Person, One Vote** - Prevents duplicate voting
- ✅ **Anonymous Voting** - Votes are recorded anonymously
- ✅ **Real-time Results** - View vote tallies
- ✅ **Offline-First** - Voter data cached locally for quick authentication

## 🏗️ Architecture

**Mobile App (React Native/Expo)**
- Local fingerprint verification
- Secure local storage for voter data
- REST API integration

**Backend (FastAPI/Python)**
- Voter registration and validation
- Vote recording and tallying
- Aadhaar number verification

## 📋 Prerequisites

- **Android Device**: Android 6.0+ with fingerprint sensor
- **Backend**: Python 3.8+
- **Mobile**: Node.js 18+, Expo CLI

## 🚀 Quick Start

See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup guide.

## 📚 Full Documentation

See [MOBILE_SETUP.md](MOBILE_SETUP.md) for complete setup and deployment guide.

## 🔒 Security

1. **Fingerprint Verification** - All actions require biometric confirmation
2. **Local-First Auth** - Fingerprint data never leaves the device
3. **Server Validation** - All requests validated against backend database
4. **Duplicate Prevention** - Cannot register same Aadhaar twice
5. **Single Vote Policy** - Each voter can vote only once
6. **Anonymous Tallying** - Votes counted separately from voter identity

## 📸 Screenshots

### Registration Flow
1. Enter name and Aadhaar
2. Scan fingerprint
3. Registration confirmed

### Voting Flow
1. Authenticate with Aadhaar and fingerprint
2. Select candidate
3. Confirm with fingerprint
4. Vote recorded

## 🛠️ Tech Stack

**Mobile App:**
- React Native (Expo)
- Expo Local Authentication API
- AsyncStorage for local data
- Fetch API for networking

**Backend:**
- FastAPI (Python)
- Pydantic for validation
- JSON file-based storage

## 📂 Project Structure

```
mobile/
├── App.js                 # Main app component
├── package.json           # Dependencies
└── app.json              # Expo config

Backend:
├── api.py                # FastAPI server
├── database/             # Data storage
│   ├── {aadhaar}/       # Voter folders
│   ├── vote_log.txt     # Audit log
│   └── vote_tally.json  # Vote counts
└── requirements-mobile.txt

Docs:
├── MOBILE_SETUP.md       # Detailed setup guide
├── QUICKSTART.md         # Quick start guide
└── README_MOBILE.md      # This file
```

## 🎨 UI/UX Features

- **Dark Theme** - Easy on the eyes
- **Clear Navigation** - Tab-based navigation
- **Visual Feedback** - Clear status indicators
- **Responsive Design** - Works on all Android screen sizes
- **Offline Support** - Core features work offline

## 🧪 Testing

### Test on Device
1. Install Expo Go from Play Store
2. Scan QR code from `npx expo start`
3. App opens with fingerprint authentication

### Test on Emulator
1. Use Android Studio AVD
2. Enable virtual fingerprint sensor
3. Run `npx expo start --android`

## 📊 API Endpoints

- `POST /register` - Register new voter
- `POST /authenticate` - Verify voter identity
- `POST /vote` - Cast vote
- `GET /results` - Get vote tally

## 🐛 Troubleshooting

**Fingerprint not working?**
- Ensure fingerprint enrolled in device settings
- Grant app biometric permissions

**Can't connect to server?**
- Verify same WiFi network
- Check IP address in App.js
- Ensure backend is running

**App crashes?**
- Clear cache: `npx expo start -c`
- Reinstall: `rm -rf node_modules && npm install`

## 🔮 Future Enhancements

- [ ] Multi-language support
- [ ] Iris/Face ID support for iOS
- [ ] Blockchain integration for vote immutability
- [ ] Real-time result dashboard
- [ ] Push notifications
- [ ] Offline queue for votes
- [ ] Admin panel

## ⚠️ Important Notes

- This is a **prototype/educational system**
- For production use, implement:
  - HTTPS/SSL encryption
  - JWT authentication
  - Database encryption
  - Secure key management
  - Rate limiting
  - Professional audit trail

## 📄 License

Educational/Prototype Use Only

## 👨‍💻 Development

**Run in development:**
```bash
# Backend
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Mobile (different terminal)
cd mobile && npx expo start
```

**Build for production:**
```bash
# Install EAS CLI
npm install -g eas-cli

# Build APK
eas build --platform android --profile preview
```

## 📞 Support

For detailed setup instructions, see:
- [Quick Start Guide](QUICKSTART.md) - 5-minute setup
- [Setup Documentation](MOBILE_SETUP.md) - Complete guide

---

**Made with ❤️ for secure, accessible, and transparent voting**
