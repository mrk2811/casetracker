import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { authApi } from "../services/api";

export default function ResetPasswordScreen({ navigation }: any) {
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleReset = async () => {
    if (!token) {
      Alert.alert("Error", "Please enter the reset code from your email");
      return;
    }
    if (!newPassword) {
      Alert.alert("Error", "Please enter a new password");
      return;
    }
    if (newPassword.length < 7) {
      Alert.alert("Error", "Password must be at least 7 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert("Error", "Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      await authApi.resetPassword({ token, new_password: newPassword });
      setSuccess(true);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        "Failed to reset password. Please try again.";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <View style={styles.iconContainer}>
            <Ionicons name="scale-outline" size={40} color="#fff" />
          </View>
          <Text style={styles.title}>NY Court Tracker</Text>
          <Text style={styles.subtitle}>Set a new password</Text>
        </View>

        <View style={styles.card}>
          {success ? (
            <>
              <View style={styles.successIcon}>
                <Ionicons
                  name="checkmark-circle-outline"
                  size={48}
                  color="#16a34a"
                />
              </View>
              <Text style={styles.cardTitle}>Password Reset!</Text>
              <Text style={styles.successMessage}>
                Your password has been updated successfully. You can now sign in
                with your new password.
              </Text>
              <TouchableOpacity
                style={styles.button}
                onPress={() => navigation.navigate("Login")}
              >
                <Text style={styles.buttonText}>Go to Sign In</Text>
              </TouchableOpacity>
            </>
          ) : (
            <>
              <Text style={styles.cardTitle}>Reset Password</Text>
              <Text style={styles.cardSubtitle}>
                Enter the code from your email and choose a new password.
              </Text>

              <Text style={styles.label}>Reset Code</Text>
              <TextInput
                style={styles.input}
                placeholder="Paste your reset code"
                placeholderTextColor="#9ca3af"
                value={token}
                onChangeText={setToken}
                autoCapitalize="none"
                autoCorrect={false}
              />

              <Text style={styles.label}>New Password</Text>
              <View style={styles.passwordContainer}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder="Min 7 characters"
                  placeholderTextColor="#9ca3af"
                  value={newPassword}
                  onChangeText={setNewPassword}
                  secureTextEntry={!showPassword}
                />
                <TouchableOpacity
                  onPress={() => setShowPassword(!showPassword)}
                  style={styles.eyeButton}
                >
                  <Ionicons
                    name={showPassword ? "eye-off-outline" : "eye-outline"}
                    size={20}
                    color="#6b7280"
                  />
                </TouchableOpacity>
              </View>

              <Text style={styles.label}>Confirm Password</Text>
              <TextInput
                style={styles.input}
                placeholder="Re-enter your new password"
                placeholderTextColor="#9ca3af"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                secureTextEntry={!showPassword}
              />

              <TouchableOpacity
                style={[styles.button, loading && styles.buttonDisabled]}
                onPress={handleReset}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.buttonText}>Reset Password</Text>
                )}
              </TouchableOpacity>
            </>
          )}

          {!success && (
            <View style={styles.footer}>
              <TouchableOpacity onPress={() => navigation.navigate("Login")}>
                <Text style={styles.link}>Back to Sign In</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  scrollContent: { flexGrow: 1, justifyContent: "center", padding: 20 },
  header: { alignItems: "center", marginBottom: 32 },
  iconContainer: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#18181b",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
  },
  title: { fontSize: 24, fontWeight: "700", color: "#18181b" },
  subtitle: { fontSize: 14, color: "#6b7280", marginTop: 4 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  cardTitle: { fontSize: 20, fontWeight: "600", color: "#18181b" },
  cardSubtitle: {
    fontSize: 14,
    color: "#6b7280",
    marginTop: 4,
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: "500",
    color: "#374151",
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: "#18181b",
    backgroundColor: "#fff",
  },
  passwordContainer: {
    flexDirection: "row",
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    backgroundColor: "#fff",
  },
  passwordInput: { flex: 1, padding: 12, fontSize: 16, color: "#18181b" },
  eyeButton: { justifyContent: "center", paddingHorizontal: 12 },
  button: {
    backgroundColor: "#18181b",
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    marginTop: 24,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  successIcon: { alignItems: "center", marginBottom: 16 },
  successMessage: {
    fontSize: 14,
    color: "#6b7280",
    marginTop: 8,
    lineHeight: 20,
  },
  footer: {
    alignItems: "center",
    marginTop: 16,
  },
  link: { color: "#18181b", fontSize: 14, fontWeight: "600" },
});
