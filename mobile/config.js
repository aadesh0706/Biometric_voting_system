// Configuration file for the mobile app
// Update these values according to your setup

export const config = {
  // Backend API Configuration
  // For Android Emulator, use: http://10.0.2.2:8000
  // For real device, use your computer's IP address (find with 'ipconfig' command)
  API_BASE_URL: "http://10.167.94.85:8000",

  // App Configuration
  APP_NAME: "Biometric Voting",
  APP_VERSION: "1.0.0",

  // Candidates List
  CANDIDATES: [
    "Candidate A",
    "Candidate B",
    "Candidate C",
    "Candidate D"
  ],

  // Face Registration Expressions (must match backend required fields)
  REGISTRATION_EXPRESSIONS: [
    { key: "neutral", label: "Keep a neutral expression" },
    { key: "blink", label: "Blink once and keep your face centered" },
    { key: "smile", label: "Smile naturally" },
    { key: "left", label: "Turn your face slightly to the left" },
    { key: "right", label: "Turn your face slightly to the right" },
  ],

  // Liveness prompts used before login verification and vote submission
  LIVENESS_PROMPTS: [
    "Look straight into the camera",
    "Blink and hold still for capture",
    "Turn your head slightly left",
    "Turn your head slightly right",
    "Smile briefly",
  ],

  LIVENESS_STEPS: 3,

  // Authentication Settings
  FINGERPRINT_PROMPT_MESSAGES: {
    register: "Scan fingerprint to register as voter",
    authenticate: "Scan fingerprint to authenticate and vote",
    vote: "Scan fingerprint to confirm your vote"
  },

  // Validation Rules
  AADHAAR_LENGTH: 12,
  MIN_NAME_LENGTH: 2,

  // UI Settings
  ENABLE_DARK_MODE: true,
  SHOW_DEBUG_INFO: false, // Set to true for development

  // Network Settings
  REQUEST_TIMEOUT: 30000, // 30 seconds
  REGISTER_REQUEST_TIMEOUT: 120000, // 2 minutes for first-time face encoding
  AUTH_REQUEST_TIMEOUT: 90000, // 90 seconds for face+liveness verification
  AUTH_RETRY_ATTEMPTS: 2,
  RETRY_ATTEMPTS: 3,
};

export default config;
