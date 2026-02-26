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
import config from "./config";

const API_BASE = config.API_BASE_URL;
const CANDIDATES = config.CANDIDATES;

export default function App() {
  const [screen, setScreen] = useState("home");
  const [name, setName] = useState("");
  const [aadhaar, setAadhaar] = useState("");
  const [authAadhaar, setAuthAadhaar] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(CANDIDATES[0]);
  const [loading, setLoading] = useState(false);
  const [authenticatedUser, setAuthenticatedUser] = useState(null);
  const [biometricSupported, setBiometricSupported] = useState(false);

  useEffect(() => {
    checkBiometricSupport();
  }, []);

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

  const handleRegister = async () => {
    if (!name.trim()) {
      Alert.alert("Error", "Please enter your full name.");
      return;
    }
    
    if (!aadhaar || aadhaar.length !== 12 || !/^\d+$/.test(aadhaar)) {
      Alert.alert("Error", "Please enter a valid 12-digit Aadhaar number.");
      return;
    }

    // Authenticate with fingerprint for registration
    const authenticated = await authenticateFingerprint(
      config.FINGERPRINT_PROMPT_MESSAGES.register
    );
    
    if (!authenticated) {
      Alert.alert("Failed", "Fingerprint authentication failed. Registration cancelled.");
      return;
    }

    setLoading(true);
    try {
      // Send registration request to backend
      const response = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name.trim(),
          aadhaar: aadhaar,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        Alert.alert("Registration Failed", data.detail || "An error occurred.");
        return;
      }

      // Store fingerprint-aadhaar mapping locally for future authentication
      await AsyncStorage.setItem(`voter_${aadhaar}`, JSON.stringify({
        name: name.trim(),
        aadhaar: aadhaar,
        registeredAt: new Date().toISOString(),
      }));

      Alert.alert(
        "Success",
        `Registration completed successfully!\n\nName: ${name}\nAadhaar: ${aadhaar}`,
        [
          {
            text: "OK",
            onPress: () => {
              setName("");
              setAadhaar("");
              setScreen("home");
            }
          }
        ]
      );
    } catch (error) {
      Alert.alert("Network Error", "Could not connect to server. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleAuthenticate = async () => {
    if (!authAadhaar || authAadhaar.length !== 12 || !/^\d+$/.test(authAadhaar)) {
      Alert.alert("Error", "Please enter a valid 12-digit Aadhaar number.");
      return;
    }

    // Check if voter is registered locally
    const voterData = await AsyncStorage.getItem(`voter_${authAadhaar}`);
    if (!voterData) {
      Alert.alert(
        "Not Registered",
        "No registration found for this Aadhaar number. Please register first."
      );
      return;
    }

    // Authenticate with fingerprint
    const authenticated = await authenticateFingerprint(
      config.FINGERPRINT_PROMPT_MESSAGES.authenticate
    );
    
    if (!authenticated) {
      Alert.alert("Failed", "Fingerprint authentication failed.");
      return;
    }

    setLoading(true);
    try {
      // Verify with backend
      const response = await fetch(`${API_BASE}/authenticate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          aadhaar: authAadhaar,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        Alert.alert("Authentication Failed", data.detail || "An error occurred.");
        return;
      }

      const voter = JSON.parse(voterData);
      setAuthenticatedUser({
        name: voter.name,
        aadhaar: authAadhaar,
      });

      Alert.alert(
        "Success",
        `Welcome ${data.name}!\n\nYou can now cast your vote.`,
        [
          {
            text: "Proceed to Vote",
            onPress: () => setScreen("vote")
          }
        ]
      );
    } catch (error) {
      Alert.alert("Network Error", "Could not connect to server. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleVote = async () => {
    if (!authenticatedUser) {
      Alert.alert("Error", "Please authenticate first.");
      setScreen("auth");
      return;
    }

    // Confirm with fingerprint before voting
    const authenticated = await authenticateFingerprint(
      config.FINGERPRINT_PROMPT_MESSAGES.vote
    );
    
    if (!authenticated) {
      Alert.alert("Cancelled", "Vote cancelled. Fingerprint authentication failed.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/vote`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          aadhaar: authenticatedUser.aadhaar,
          candidate: selectedCandidate,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        Alert.alert("Vote Failed", data.detail || "An error occurred.");
        return;
      }

      Alert.alert(
        "Vote Recorded",
        `Thank you for voting!\n\nYour vote has been recorded securely and anonymously.`,
        [
          {
            text: "OK",
            onPress: () => {
              setAuthenticatedUser(null);
              setAuthAadhaar("");
              setSelectedCandidate(CANDIDATES[0]);
              setScreen("home");
            }
          }
        ]
      );
    } catch (error) {
      Alert.alert("Network Error", "Could not connect to server. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>🗳️ Biometric Voting System</Text>
        <Text style={styles.subtitle}>Fingerprint-Secured Voting</Text>

        {!biometricSupported && (
          <View style={styles.warningCard}>
            <Text style={styles.warningText}>
              ⚠️ Fingerprint authentication is not available on this device.
            </Text>
          </View>
        )}

        <View style={styles.nav}>
          <TouchableOpacity
            style={[styles.tab, screen === "home" && styles.activeTab]}
            onPress={() => setScreen("home")}
          >
            <Text style={styles.tabText}>🏠 Home</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, screen === "register" && styles.activeTab]}
            onPress={() => setScreen("register")}
          >
            <Text style={styles.tabText}>📝 Register</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, screen === "auth" && styles.activeTab]}
            onPress={() => setScreen("auth")}
          >
            <Text style={styles.tabText}>🔐 Authenticate</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, screen === "vote" && styles.activeTab]}
            onPress={() => setScreen("vote")}
            disabled={!authenticatedUser}
          >
            <Text style={[styles.tabText, !authenticatedUser && styles.disabledText]}>
              🗳️ Vote
            </Text>
          </TouchableOpacity>
        </View>

        {screen === "home" && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Welcome to Biometric Voting</Text>
            <Text style={styles.cardText}>
              This secure voting system uses your device's fingerprint sensor to ensure
              one person, one vote.
            </Text>
            <Text style={styles.cardText}>
              {"\n"}📱 <Text style={styles.bold}>How it works:</Text>
            </Text>
            <Text style={styles.cardText}>
              1. Register with your Aadhaar number and fingerprint{"\n"}
              2. Authenticate using your fingerprint{"\n"}
              3. Cast your vote securely and anonymously
            </Text>
            <Text style={styles.cardText}>
              {"\n"}🔒 <Text style={styles.bold}>Security Features:</Text>
            </Text>
            <Text style={styles.cardText}>
              • Fingerprint verification for all actions{"\n"}
              • Duplicate voter detection{"\n"}
              • One vote per Aadhaar number{"\n"}
              • Anonymous vote recording
            </Text>
          </View>
        )}

        {screen === "register" && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>📝 Voter Registration</Text>
            <Text style={styles.cardText}>
              Register as a new voter using your Aadhaar number and fingerprint.
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
                👆 You will be prompted to scan your fingerprint after clicking Register.
              </Text>
            </View>

            <TouchableOpacity
              style={[styles.primaryButton, loading && styles.disabledButton]}
              onPress={handleRegister}
              disabled={loading || !biometricSupported}
            >
              <Text style={styles.primaryButtonText}>
                {loading ? "Registering..." : "Register with Fingerprint"}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {screen === "auth" && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>🔐 Voter Authentication</Text>
            <Text style={styles.cardText}>
              Authenticate with your Aadhaar number and fingerprint to access the voting portal.
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
                👆 You will be prompted to scan your fingerprint for authentication.
              </Text>
            </View>

            <TouchableOpacity
              style={[styles.primaryButton, loading && styles.disabledButton]}
              onPress={handleAuthenticate}
              disabled={loading || !biometricSupported}
            >
              <Text style={styles.primaryButtonText}>
                {loading ? "Authenticating..." : "Authenticate with Fingerprint"}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {screen === "vote" && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>🗳️ Cast Your Vote</Text>
            
            {authenticatedUser ? (
              <>
                <View style={styles.userInfo}>
                  <Text style={styles.userInfoText}>
                    ✅ Authenticated as: {authenticatedUser.name}
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
                    👆 You will be prompted to confirm with your fingerprint before submitting.
                  </Text>
                </View>

                <TouchableOpacity
                  style={[styles.voteButton, loading && styles.disabledButton]}
                  onPress={handleVote}
                  disabled={loading || !biometricSupported}
                >
                  <Text style={styles.voteButtonText}>
                    {loading ? "Submitting Vote..." : "Submit Vote"}
                  </Text>
                </TouchableOpacity>
              </>
            ) : (
              <View style={styles.notAuthCard}>
                <Text style={styles.notAuthText}>
                  ⚠️ Please authenticate first to access the voting portal.
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
});
