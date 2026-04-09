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

export default function ResetPasswordScreen({ navigation, route }: any) {
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async () => {
    if (!token) {
      Alert.alert("Error", "Please enter the reset code from your email");
      return;
    }
    if (!newPassword) {
      Alert.alert("Error", "Please enter a new password");
      return;
    }
    if (newPassword.length < 6) {
      Alert.alert("Error", "Password must be at least 6 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert("Error", "Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      await authApi.resetPassword(token.trim(), newPassword);
      setSuccess(true);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail || "Failed to reset password. Please try again.";
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
            <Ionicons name="lock-closed-outline" size={40} color="#fff" />
          </View>
          <Text style={styles.title}>Reset Password</Text>
          <Text style={styles.subtitle}>
            {success
              ? "Your password has been reset"
              : "Enter the code from your email and your new password"}
          </Text>
        </View>

        <View style={styles.card}>
          {success ? (
            <>
              <View style={styles.successIcon}>
                <Ionicons
                  name="checkmark-circle-outline"
                  size={64}
                  color="#22c55e"
                />
              </View>
              <Text style={styles.successText}>
                Your password has been reset successfully. You can now sign in
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
              <Text style={styles.cardTitle}>Set New Password</Text>
              <Text style={styles.cardSubtitle}>
                Enter the reset code and choose a new password
              </Text>

              <Text style={styles.label}>Reset Code</Text>
              <TextInput
                style={styles.input}
                placeholder="Paste the code from your email"
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
                  placeholder="Enter new password"
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
              <View style={styles.passwordContainer}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder="Confirm new password"
                  placeholderTextColor="#9ca3af"
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  secureTextEntry={!showPassword}
                />
              </View>

              <TouchableOpacity
                style={[styles.button, loading && styles.buttonDisabled]}
                onPress={handleSubmit}
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

          <View style={styles.footer}>
            <Text style={styles.footerText}>Remember your password? </Text>
            <TouchableOpacity onPress={() => navigation.navigate("Login")}>
              <Text style={styles.link}>Sign In</Text>
            </TouchableOpacity>
          </View>
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
  subtitle: { fontSize: 14, color: "#6b7280", marginTop: 4, textAlign: "center" },
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
  successIcon: { alignItems: "center", marginBottom: 16, marginTop: 8 },
  successText: {
    fontSize: 15,
    color: "#374151",
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 8,
  },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    marginTop: 16,
  },
  footerText: { color: "#6b7280", fontSize: 14 },
  link: { color: "#18181b", fontSize: 14, fontWeight: "600" },
});
