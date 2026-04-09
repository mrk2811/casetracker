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

export default function ForgotPasswordScreen({ navigation }: any) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async () => {
    if (!email) {
      Alert.alert("Error", "Please enter your email address");
      return;
    }
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail || "Something went wrong. Please try again.";
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
            <Ionicons name="key-outline" size={40} color="#fff" />
          </View>
          <Text style={styles.title}>Forgot Password</Text>
          <Text style={styles.subtitle}>
            {sent
              ? "Check your email for a reset code"
              : "Enter your email to receive a reset code"}
          </Text>
        </View>

        <View style={styles.card}>
          {sent ? (
            <>
              <View style={styles.successIcon}>
                <Ionicons name="mail-outline" size={48} color="#18181b" />
              </View>
              <Text style={styles.successText}>
                If an account with that email exists, we've sent a password
                reset code. Check your inbox and spam folder.
              </Text>
              <TouchableOpacity
                style={styles.button}
                onPress={() => navigation.navigate("ResetPassword", { email })}
              >
                <Text style={styles.buttonText}>Enter Reset Code</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={() => {
                  setSent(false);
                  setEmail("");
                }}
              >
                <Text style={styles.secondaryButtonText}>
                  Resend to a different email
                </Text>
              </TouchableOpacity>
            </>
          ) : (
            <>
              <Text style={styles.cardTitle}>Reset Your Password</Text>
              <Text style={styles.cardSubtitle}>
                We'll send a reset code to your email address
              </Text>

              <Text style={styles.label}>Email</Text>
              <TextInput
                style={styles.input}
                placeholder="you@example.com"
                placeholderTextColor="#9ca3af"
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
              />

              <TouchableOpacity
                style={[styles.button, loading && styles.buttonDisabled]}
                onPress={handleSubmit}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.buttonText}>Send Reset Code</Text>
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
  button: {
    backgroundColor: "#18181b",
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    marginTop: 24,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  secondaryButton: {
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    marginTop: 12,
    borderWidth: 1,
    borderColor: "#d1d5db",
  },
  secondaryButtonText: { color: "#374151", fontSize: 14, fontWeight: "500" },
  successIcon: { alignItems: "center", marginBottom: 16 },
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
