import React, { useEffect, useState } from "react";
import {
  Alert,
  SafeAreaView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import * as LocalAuthentication from "expo-local-authentication";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ImagePicker from "expo-image-picker";
import * as ImageManipulator from "expo-image-manipulator";
import config from "./config";

const API_BASE = config.API_BASE_URL;
const CANDIDATES = config.CANDIDATES;
const REGISTER_EXPRESSIONS = config.REGISTRATION_EXPRESSIONS;

const randomLivenessPrompts = () => {
  const pool = [...config.LIVENESS_PROMPTS];
  const count = Math.min(config.LIVENESS_STEPS, pool.length);
  const prompts = [];

  while (prompts.length < count) {
    const index = Math.floor(Math.random() * pool.length);
    prompts.push(pool.splice(index, 1)[0]);
  }

  return prompts.map((label, index) => ({ key: `live_${index}`, label }));
};

const buildImageFormField = (uri, name) => ({
  uri,
  name,
  type: "image/jpeg",
});

const optimizeCaptureForUpload = async (uri) => {
  const result = await ImageManipulator.manipulateAsync(
    uri,
    [{ resize: { width: 720 } }],
    { compress: 0.55, format: ImageManipulator.SaveFormat.JPEG }
  );
  return result.uri;
};

const getErrorMessage = async (response) => {
  try {
    const data = await response.json();
    return data.detail || data.message || "An error occurred.";
  } catch (error) {
    return "An error occurred.";
  }
};

const getResponseData = async (response) => {
  try {
    return await response.json();
  } catch (error) {
    return null;
  }
};

export default function App() {
  const [screen, setScreen] = useState("home");
  const [name, setName] = useState("");
  const [aadhaar, setAadhaar] = useState("");
  const [authAadhaar, setAuthAadhaar] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(CANDIDATES[0]);
  const [loading, setLoading] = useState(false);
  const [authenticatedUser, setAuthenticatedUser] = useState(null);
  const [biometricSupported, setBiometricSupported] = useState(false);
  const [authToken, setAuthToken] = useState("");
  const [cameraFlow, setCameraFlow] = useState(null);

  useEffect(() => {
    checkBiometricSupport();
  }, []);

  const fetchWithTimeout = async (url, options = {}) => {
    const { timeoutMs, ...fetchOptions } = options;
    const controller = new AbortController();
    const requestTimeout = timeoutMs || config.REQUEST_TIMEOUT;
    const timeoutId = setTimeout(() => controller.abort(), requestTimeout);
    try {
      return await fetch(url, { ...fetchOptions, signal: controller.signal });
    } finally {
      clearTimeout(timeoutId);
    }
  };

  const checkBiometricSupport = async () => {
    const compatible = await LocalAuthentication.hasHardwareAsync();
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    setBiometricSupported(compatible && enrolled);
    
    if (!compatible) {
      Alert.alert(
        "Not Supported",
        "This device does not support fingerprint authentication."
      );
    } else if (!enrolled) {
      Alert.alert(
        "Setup Required",
        "Please set up fingerprint authentication in your device settings."
      );
    }
  };

  const authenticateFingerprint = async (promptMessage) => {
    if (!biometricSupported) {
      Alert.alert("Error", "Fingerprint authentication not available.");
      return false;
    }

    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: promptMessage,
        disableDeviceFallback: false,
        cancelLabel: "Cancel",
      });
      return result.success;
    } catch (error) {
      Alert.alert("Error", "Fingerprint authentication failed.");
      return false;
    }
  };

  const ensureCameraAccess = async () => {
    const existing = await ImagePicker.getCameraPermissionsAsync();
    if (existing.granted) {
      return true;
    }

    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("Permission Required", "Camera permission is required for face verification.");
      return false;
    }

    return true;
  };

  const startCameraFlow = async (type) => {
    const hasPermission = await ensureCameraAccess();
    if (!hasPermission) {
      return;
    }

    const steps = type === "register" ? REGISTER_EXPRESSIONS : randomLivenessPrompts();
    setCameraFlow({ type, stepIndex: 0, steps, capturedUris: [] });
    setScreen("camera");
  };

  const syncLocalRegistrationCache = async (aadhaarNumber, nameValue) => {
    await AsyncStorage.setItem(
      `voter_${aadhaarNumber}`,
      JSON.stringify({
        name: nameValue || "Voter",
        aadhaar: aadhaarNumber,
        syncedAt: new Date().toISOString(),
        mode: "face+liveness",
      })
    );
  };

  const checkRegistrationStatus = async (aadhaarNumber) => {
    const response = await fetchWithTimeout(`${API_BASE}/registration-status/${aadhaarNumber}`, {
      method: "GET",
      timeoutMs: Math.max(config.REQUEST_TIMEOUT, 45000),
    });

    const data = await getResponseData(response);
    if (!response.ok) {
      return { registered: false, name: null };
    }

    return {
      registered: Boolean(data?.registered),
      name: data?.name || null,
    };
  };

  const uploadRegistration = async (capturedUris) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("name", name.trim());
      formData.append("aadhaar", aadhaar);

      REGISTER_EXPRESSIONS.forEach((expression, index) => {
        formData.append(expression.key, buildImageFormField(capturedUris[index], `${expression.key}.jpg`));
      });

      const response = await fetchWithTimeout(`${API_BASE}/register`, {
        method: "POST",
        body: formData,
        timeoutMs: config.REGISTER_REQUEST_TIMEOUT,
      });

      const data = await getResponseData(response);

      if (!response.ok) {
        const detail = data?.detail || data?.message || "An error occurred.";

        // If backend already has this Aadhaar, keep app state consistent instead of blocking login.
        if (response.status === 409 && /already registered|in progress|completed/i.test(detail)) {
          await syncLocalRegistrationCache(aadhaar, name.trim());

          Alert.alert("Already Registered", "This Aadhaar is already registered. You can proceed to verification.", [
            {
              text: "OK",
              onPress: () => {
                setName("");
                setAadhaar("");
                setScreen("auth");
              },
            },
          ]);
          return;
        }

        Alert.alert("Registration Failed", detail);
        return;
      }

      await syncLocalRegistrationCache(aadhaar, name.trim());

      Alert.alert("Success", "Registration completed with face liveness and fingerprint checks.", [
        {
          text: "OK",
          onPress: () => {
            setName("");
            setAadhaar("");
            setScreen("home");
          },
        },
      ]);
    } catch (error) {
      if (error?.name === "AbortError") {
        try {
          const status = await checkRegistrationStatus(aadhaar);
          if (status.registered) {
            await syncLocalRegistrationCache(aadhaar, status.name || name.trim());
            Alert.alert("Registration Completed", "Server saved your registration. Proceeding to verification.", [
              {
                text: "OK",
                onPress: () => {
                  setName("");
                  setAadhaar("");
                  setAuthAadhaar(aadhaar);
                  setScreen("auth");
                },
              },
            ]);
            return;
          }
        } catch (statusError) {
          // Fall back to timeout message if status check itself fails.
        }

        Alert.alert("Timeout", "Registration took too long. Please wait a few seconds and try Verify/Login directly.");
      } else {
        Alert.alert("Network Error", "Could not connect to server. Please check your connection.");
      }
    } finally {
      setLoading(false);
    }
  };

  const performFaceAuthenticate = async (aadhaarNumber, imageUris) => {
    if (!imageUris?.length) {
      throw new Error("No face captures found for verification.");
    }

    const formData = new FormData();
    formData.append("aadhaar", aadhaarNumber);

    const primaryUri = imageUris[imageUris.length - 1];
    formData.append("image", buildImageFormField(primaryUri, "auth_primary.jpg"));

    imageUris.forEach((uri, index) => {
      formData.append("liveness_images", buildImageFormField(uri, `liveness_${index}.jpg`));
    });

    let response = null;
    let lastError = null;

    for (let attempt = 1; attempt <= config.AUTH_RETRY_ATTEMPTS; attempt += 1) {
      try {
        response = await fetchWithTimeout(`${API_BASE}/authenticate`, {
          method: "POST",
          body: formData,
          timeoutMs: config.AUTH_REQUEST_TIMEOUT,
        });
        break;
      } catch (error) {
        lastError = error;
        const isAbort = error?.name === "AbortError";
        if (!isAbort || attempt === config.AUTH_RETRY_ATTEMPTS) {
          throw error;
        }
      }
    }

    if (!response) {
      throw lastError || new Error("Authentication request failed");
    }

    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }

    return response.json();
  };

  const completeAuthFlow = async (capturedUris) => {
    setLoading(true);
    try {
      const data = await performFaceAuthenticate(authAadhaar, capturedUris);

      setAuthenticatedUser({ name: data.name || "Voter", aadhaar: authAadhaar });
      setAuthToken(data.token || "");

      // Keep local cache in sync with backend registration for future offline hints.
      await syncLocalRegistrationCache(authAadhaar, data.name || "Voter");

      Alert.alert("Verification Success", `Welcome ${data.name || "Voter"}. You can now vote.`, [
        {
          text: "Proceed to Vote",
          onPress: () => setScreen("vote"),
        },
      ]);
    } catch (error) {
      if (error?.name === "AbortError") {
        Alert.alert(
          "Verification Timeout",
          "Face verification took too long. Please keep good lighting and try again."
        );
      } else {
        Alert.alert("Authentication Failed", error.message || "Face verification failed.");
      }
      setScreen("auth");
    } finally {
      setLoading(false);
    }
  };

  const completeVoteFlow = async (capturedUris) => {
    if (!authenticatedUser) {
      Alert.alert("Error", "Please authenticate first.");
      setScreen("auth");
      return;
    }

    setLoading(true);
    try {
      // Re-authenticate with a fresh liveness frame before final vote submission.
      const freshAuth = await performFaceAuthenticate(authenticatedUser.aadhaar, capturedUris);
      const tokenToUse = freshAuth.token || authToken;

      const response = await fetchWithTimeout(`${API_BASE}/vote`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokenToUse}`,
        },
        body: JSON.stringify({ candidate: selectedCandidate }),
      });

      if (!response.ok) {
        Alert.alert("Vote Failed", await getErrorMessage(response));
        setScreen("vote");
        return;
      }

      Alert.alert("Vote Recorded", "Your vote was recorded after successful liveness and biometric checks.", [
        {
          text: "OK",
          onPress: () => {
            setAuthenticatedUser(null);
            setAuthAadhaar("");
            setAuthToken("");
            setSelectedCandidate(CANDIDATES[0]);
            setScreen("home");
          },
        },
      ]);
    } catch (error) {
      Alert.alert("Error", error.message || "Unable to submit vote.");
      setScreen("vote");
    } finally {
      setLoading(false);
    }
  };

  const completeCameraFlow = async (flowType, capturedUris) => {
    if (flowType === "register") {
      await uploadRegistration(capturedUris);
      return;
    }

    if (flowType === "auth") {
      await completeAuthFlow(capturedUris);
      return;
    }

    if (flowType === "vote") {
      await completeVoteFlow(capturedUris);
    }
  };

  const handleCapture = async () => {
    if (!cameraFlow) {
      return;
    }

    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 0.65,
      });

      if (result.canceled || !result.assets?.length || !result.assets[0]?.uri) {
        Alert.alert("Capture Cancelled", "Camera capture was cancelled.");
        return;
      }

      const shot = result.assets[0];
      if (!shot.uri) {
        Alert.alert("Capture Failed", "Could not capture image. Try again.");
        return;
      }

      const optimizedUri = await optimizeCaptureForUpload(shot.uri);

      const updatedUris = [...cameraFlow.capturedUris, optimizedUri];

      if (cameraFlow.stepIndex < cameraFlow.steps.length - 1) {
        setCameraFlow({ ...cameraFlow, stepIndex: cameraFlow.stepIndex + 1, capturedUris: updatedUris });
        return;
      }

      const flowType = cameraFlow.type;
      setCameraFlow(null);
      setScreen(flowType === "register" ? "register" : flowType === "auth" ? "auth" : "vote");
      await completeCameraFlow(flowType, updatedUris);
    } catch (error) {
      Alert.alert("Capture Failed", "Unable to capture from camera.");
    }
  };

  const cancelCameraFlow = () => {
    const flowType = cameraFlow?.type;
    setCameraFlow(null);
    setScreen(flowType === "register" ? "register" : flowType === "vote" ? "vote" : "auth");
  };

  const handleRegister = async () => {
    if (!name.trim()) {
      Alert.alert("Error", "Please enter your full name.");
      return;
    }
    
    if (!aadhaar || aadhaar.length !== 12 || !/^\d+$/.test(aadhaar)) {
      Alert.alert("Error", "Please enter a valid 12-digit Aadhaar number.");
      return;
    }

    const authenticated = await authenticateFingerprint(
      config.FINGERPRINT_PROMPT_MESSAGES.register
    );

    if (!authenticated) {
      Alert.alert("Failed", "Fingerprint authentication failed. Registration cancelled.");
      return;
    }

    await startCameraFlow("register");
  };

  const handleAuthenticate = async () => {
    if (!authAadhaar || authAadhaar.length !== 12 || !/^\d+$/.test(authAadhaar)) {
      Alert.alert("Error", "Please enter a valid 12-digit Aadhaar number.");
      return;
    }

    const authenticated = await authenticateFingerprint(
      config.FINGERPRINT_PROMPT_MESSAGES.authenticate
    );

    if (!authenticated) {
      Alert.alert("Failed", "Fingerprint authentication failed.");
      return;
    }

    await startCameraFlow("auth");
  };

  const handleVote = async () => {
    if (!authenticatedUser) {
      Alert.alert("Error", "Please authenticate first.");
      setScreen("auth");
      return;
    }

    const authenticated = await authenticateFingerprint(
      config.FINGERPRINT_PROMPT_MESSAGES.vote
    );

    if (!authenticated) {
      Alert.alert("Cancelled", "Vote cancelled. Fingerprint authentication failed.");
      return;
    }

    await startCameraFlow("vote");
  };

  if (screen === "camera" && cameraFlow) {
    const activeStep = cameraFlow.steps[cameraFlow.stepIndex];
    return (
      <SafeAreaView style={styles.cameraScreenContainer}>
        <View style={styles.cameraHeader}>
          <Text style={styles.cameraTitle}>Face Capture</Text>
          <Text style={styles.cameraSubtitle}>
            Step {cameraFlow.stepIndex + 1} of {cameraFlow.steps.length}
          </Text>
          <Text style={styles.cameraInstruction}>{activeStep?.label}</Text>
        </View>

        <View style={styles.cameraPlaceholder}>
          <Text style={styles.cameraPlaceholderText}>
            Tap "Capture Step" to open your phone camera for this liveness step.
          </Text>
        </View>

        <View style={styles.cameraFooter}>
          <Text style={styles.livenessInfo}>
            Keep your face clearly visible. Each capture is used for liveness and identity verification.
          </Text>
          <TouchableOpacity style={styles.primaryButton} onPress={handleCapture} disabled={loading}>
            <Text style={styles.primaryButtonText}>Capture Step</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.cancelButton} onPress={cancelCameraFlow} disabled={loading}>
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Biometric Voting System</Text>
        <Text style={styles.subtitle}>Fingerprint + Face Liveness Voting</Text>

        {!biometricSupported && (
          <View style={styles.warningCard}>
            <Text style={styles.warningText}>
              Fingerprint authentication is not available on this device.
            </Text>
          </View>
        )}

        <View style={styles.nav}>
          <TouchableOpacity
            style={[styles.tab, screen === "home" && styles.activeTab]}
            onPress={() => setScreen("home")}
          >
            <Text style={styles.tabText}>Home</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, screen === "register" && styles.activeTab]}
            onPress={() => setScreen("register")}
          >
            <Text style={styles.tabText}>Register</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, screen === "auth" && styles.activeTab]}
            onPress={() => setScreen("auth")}
          >
            <Text style={styles.tabText}>Verify</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, screen === "vote" && styles.activeTab]}
            onPress={() => setScreen("vote")}
            disabled={!authenticatedUser}
          >
            <Text style={[styles.tabText, !authenticatedUser && styles.disabledText]}>
              Vote
            </Text>
          </TouchableOpacity>
        </View>

        {screen === "home" && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Welcome to Biometric Voting</Text>
            <Text style={styles.cardText}>
              This app now runs the Python face recognition workflow directly from Android.
            </Text>
            <Text style={styles.cardText}>
              <Text style={styles.bold}>How it works:</Text>
            </Text>
            <Text style={styles.cardText}>
              1. Register with Aadhaar, fingerprint, and 5 face expressions{"\n"}
              2. Verify login with fingerprint and live face challenge{"\n"}
              3. Confirm vote with fingerprint and second liveness challenge
            </Text>
            <Text style={styles.cardText}>
              <Text style={styles.bold}>Security Features:</Text>
            </Text>
            <Text style={styles.cardText}>
              • Face duplicate detection in backend{"\n"}
              • Challenge-based live face capture{"\n"}
              • Fingerprint checks for every critical action{"\n"}
              • One vote per Aadhaar enforced server-side
            </Text>
          </View>
        )}

        {screen === "register" && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Voter Registration</Text>
            <Text style={styles.cardText}>
              Registration includes fingerprint and a 5-step face liveness capture.
            </Text>

            <TextInput
              style={styles.input}
              placeholder="Enter Full Name"
              placeholderTextColor="#64748b"
              value={name}
              onChangeText={setName}
              editable={!loading}
            />

            <TextInput
              style={styles.input}
              placeholder="Enter Aadhaar Number (12 digits)"
              placeholderTextColor="#64748b"
              keyboardType="numeric"
              value={aadhaar}
              onChangeText={setAadhaar}
              maxLength={12}
              editable={!loading}
            />

            <View style={styles.infoBox}>
              <Text style={styles.infoText}>
                You will scan fingerprint first, then capture neutral, blink, smile, left, and right face images.
              </Text>
            </View>

            <TouchableOpacity
              style={[styles.primaryButton, loading && styles.disabledButton]}
              onPress={handleRegister}
              disabled={loading || !biometricSupported}
            >
              <Text style={styles.primaryButtonText}>
                {loading ? "Registering..." : "Start Registration"}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {screen === "auth" && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Verification / Login</Text>
            <Text style={styles.cardText}>
              Login verification requires Aadhaar, fingerprint, and live face challenge.
            </Text>

            <TextInput
              style={styles.input}
              placeholder="Enter Aadhaar Number (12 digits)"
              placeholderTextColor="#64748b"
              keyboardType="numeric"
              value={authAadhaar}
              onChangeText={setAuthAadhaar}
              maxLength={12}
              editable={!loading}
            />

            <View style={styles.infoBox}>
              <Text style={styles.infoText}>
                After fingerprint, complete liveness prompts and capture 3 face frames.
              </Text>
            </View>

            <TouchableOpacity
              style={[styles.primaryButton, loading && styles.disabledButton]}
              onPress={handleAuthenticate}
              disabled={loading || !biometricSupported}
            >
              <Text style={styles.primaryButtonText}>
                {loading ? "Authenticating..." : "Verify and Login"}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {screen === "vote" && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Cast Your Vote</Text>
            
            {authenticatedUser ? (
              <>
                <View style={styles.userInfo}>
                  <Text style={styles.userInfoText}>
                    Authenticated as: {authenticatedUser.name}
                  </Text>
                </View>

                <Text style={styles.cardText}>
                  Select your preferred candidate:
                </Text>

                {CANDIDATES.map((candidate) => (
                  <TouchableOpacity
                    key={candidate}
                    style={[
                      styles.option,
                      selectedCandidate === candidate && styles.selectedOption
                    ]}
                    onPress={() => setSelectedCandidate(candidate)}
                    disabled={loading}
                  >
                    <Text style={[
                      styles.optionText,
                      selectedCandidate === candidate && styles.selectedOptionText
                    ]}>
                      {selectedCandidate === candidate ? "✓ " : ""}{candidate}
                    </Text>
                  </TouchableOpacity>
                ))}

                <View style={styles.infoBox}>
                  <Text style={styles.infoText}>
                    Final vote submission will run fingerprint + face liveness re-check.
                  </Text>
                </View>

                <TouchableOpacity
                  style={[styles.voteButton, loading && styles.disabledButton]}
                  onPress={handleVote}
                  disabled={loading || !biometricSupported}
                >
                  <Text style={styles.voteButtonText}>
                    {loading ? "Submitting Vote..." : "Run Liveness and Submit Vote"}
                  </Text>
                </TouchableOpacity>
              </>
            ) : (
              <View style={styles.notAuthCard}>
                <Text style={styles.notAuthText}>
                  Please verify first to access the voting portal.
                </Text>
                <TouchableOpacity
                  style={styles.button}
                  onPress={() => setScreen("auth")}
                >
                  <Text style={styles.buttonText}>Go to Authentication</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        )}

        {loading && (
          <View style={styles.loadingOverlay}>
            <ActivityIndicator size="large" color="#0ea5e9" />
          </View>
        )}

        {authenticatedUser?.aadhaar ? (
          <View style={styles.debugCard}>
            <Text style={styles.debugText}>Logged in Aadhaar: {authenticatedUser.aadhaar}</Text>
            <Text style={styles.debugText}>Token active: {authToken ? "Yes" : "No"}</Text>
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  title: {
    fontSize: 28,
    color: "#f8fafc",
    fontWeight: "700",
    marginBottom: 4,
    textAlign: "center",
  },
  subtitle: {
    fontSize: 16,
    color: "#94a3b8",
    marginBottom: 16,
    textAlign: "center",
  },
  warningCard: {
    backgroundColor: "#7f1d1d",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  warningText: {
    color: "#fecaca",
    fontSize: 14,
    textAlign: "center",
  },
  nav: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 20,
    justifyContent: "center",
  },
  tab: {
    backgroundColor: "#1e293b",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: "transparent",
  },
  activeTab: {
    backgroundColor: "#1e40af",
    borderColor: "#3b82f6",
  },
  tabText: {
    color: "#e2e8f0",
    fontWeight: "600",
    fontSize: 14,
  },
  disabledText: {
    color: "#64748b",
  },
  card: {
    backgroundColor: "#1e293b",
    padding: 20,
    borderRadius: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#334155",
  },
  cardTitle: {
    fontSize: 22,
    color: "#f1f5f9",
    fontWeight: "700",
    marginBottom: 12,
  },
  cardText: {
    color: "#cbd5e1",
    marginBottom: 12,
    fontSize: 15,
    lineHeight: 22,
  },
  bold: {
    fontWeight: "700",
    color: "#e2e8f0",
  },
  input: {
    backgroundColor: "#0f172a",
    color: "#f8fafc",
    padding: 14,
    borderRadius: 8,
    marginBottom: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: "#475569",
  },
  infoBox: {
    backgroundColor: "#1e40af",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#60a5fa",
  },
  infoText: {
    color: "#dbeafe",
    fontSize: 14,
    lineHeight: 20,
  },
  button: {
    backgroundColor: "#2563eb",
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 10,
  },
  buttonText: {
    color: "#fff",
    fontWeight: "600",
    fontSize: 16,
  },
  primaryButton: {
    backgroundColor: "#059669",
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: "center",
    elevation: 3,
  },
  primaryButtonText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 16,
  },
  voteButton: {
    backgroundColor: "#dc2626",
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: "center",
    elevation: 3,
  },
  voteButtonText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 16,
  },
  disabledButton: {
    backgroundColor: "#475569",
    opacity: 0.6,
  },
  option: {
    backgroundColor: "#0f172a",
    padding: 14,
    borderRadius: 8,
    marginBottom: 10,
    borderWidth: 2,
    borderColor: "#475569",
  },
  selectedOption: {
    backgroundColor: "#0ea5e9",
    borderColor: "#0ea5e9",
  },
  optionText: {
    color: "#e2e8f0",
    fontSize: 16,
    fontWeight: "500",
  },
  selectedOptionText: {
    color: "#fff",
    fontWeight: "700",
  },
  userInfo: {
    backgroundColor: "#065f46",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#10b981",
  },
  userInfoText: {
    color: "#d1fae5",
    fontSize: 15,
    fontWeight: "600",
  },
  notAuthCard: {
    backgroundColor: "#7c2d12",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  notAuthText: {
    color: "#fed7aa",
    fontSize: 15,
    marginBottom: 12,
    textAlign: "center",
  },
  loadingOverlay: {
    alignItems: "center",
    marginVertical: 20,
  },
  debugCard: {
    marginTop: 8,
    padding: 12,
    borderRadius: 8,
    backgroundColor: "#1f2937",
    borderWidth: 1,
    borderColor: "#374151",
  },
  debugText: {
    color: "#9ca3af",
    fontSize: 12,
  },
  cameraScreenContainer: {
    flex: 1,
    backgroundColor: "#020617",
    padding: 16,
  },
  cameraHeader: {
    marginBottom: 12,
  },
  cameraTitle: {
    color: "#f8fafc",
    fontSize: 22,
    fontWeight: "700",
    textAlign: "center",
  },
  cameraSubtitle: {
    color: "#94a3b8",
    fontSize: 14,
    textAlign: "center",
    marginTop: 4,
  },
  cameraInstruction: {
    color: "#e2e8f0",
    fontSize: 16,
    textAlign: "center",
    marginTop: 10,
  },
  cameraWrapper: {
    flex: 1,
    overflow: "hidden",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#334155",
  },
  cameraPlaceholder: {
    flex: 1,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#334155",
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  cameraPlaceholderText: {
    color: "#cbd5e1",
    fontSize: 15,
    textAlign: "center",
    lineHeight: 22,
  },
  cameraFooter: {
    marginTop: 14,
    gap: 10,
  },
  livenessInfo: {
    color: "#cbd5e1",
    textAlign: "center",
    fontSize: 13,
  },
  cancelButton: {
    backgroundColor: "#475569",
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: "center",
  },
  cancelButtonText: {
    color: "#f8fafc",
    fontWeight: "600",
    fontSize: 15,
  },
});
