// Configuration file for the mobile app
// Update these values according to your setup

export const config = {
  // Backend API Configuration
  // For Android Emulator, use: http://10.0.2.2:8000
  // For real device, use your computer's IP address (find with 'ipconfig' command)
  API_BASE_URL: "http://10.194.221.85:8000",

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
  RETRY_ATTEMPTS: 3,
};

export default config;
