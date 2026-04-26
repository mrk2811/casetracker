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
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../context/AuthContext";
import { authApi } from "../services/api";
import { showAlert } from "../utils/alert";

export default function RegisterScreen({ navigation }: any) {
  const { login } = useAuth();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    attorney_reg_number: "",
    password: "",
    confirmPassword: "",
  });
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (!form.first_name || !form.last_name || !form.email || !form.password) {
      showAlert("Error", "Please fill in all required fields");
      return;
    }
    if (form.password.length < 7) {
      showAlert("Error", "Password must be at least 7 characters");
      return;
    }
    if (form.password !== form.confirmPassword) {
      showAlert("Error", "Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      const res = await authApi.register({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
        attorney_reg_number: form.attorney_reg_number || undefined,
      });
      await login(res.data.access_token, res.data.user);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Registration failed";
      showAlert("Registration Failed", msg);
    } finally {
      setLoading(false);
    }
  };

  const updateForm = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
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
          <Text style={styles.subtitle}>Create your account</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Create Account</Text>
          <Text style={styles.cardSubtitle}>Fill in your details to get started</Text>

          <View style={styles.row}>
            <View style={styles.halfField}>
              <Text style={styles.label}>First Name *</Text>
              <TextInput
                style={styles.input}
                value={form.first_name}
                onChangeText={(v) => updateForm("first_name", v)}
                placeholder="First"
                placeholderTextColor="#9ca3af"
              />
            </View>
            <View style={styles.halfField}>
              <Text style={styles.label}>Last Name *</Text>
              <TextInput
                style={styles.input}
                value={form.last_name}
                onChangeText={(v) => updateForm("last_name", v)}
                placeholder="Last"
                placeholderTextColor="#9ca3af"
              />
            </View>
          </View>

          <Text style={styles.label}>Email *</Text>
          <TextInput
            style={styles.input}
            value={form.email}
            onChangeText={(v) => updateForm("email", v)}
            placeholder="you@example.com"
            placeholderTextColor="#9ca3af"
            keyboardType="email-address"
            autoCapitalize="none"
          />

          <Text style={styles.label}>
            Attorney Registration Number{" "}
            <Text style={styles.optional}>(optional)</Text>
          </Text>
          <TextInput
            style={styles.input}
            value={form.attorney_reg_number}
            onChangeText={(v) => updateForm("attorney_reg_number", v)}
            placeholderTextColor="#9ca3af"
          />

          <Text style={styles.label}>Password *</Text>
          <TextInput
            style={styles.input}
            value={form.password}
            onChangeText={(v) => updateForm("password", v)}
            placeholder="Min 7 characters"
            placeholderTextColor="#9ca3af"
            secureTextEntry
          />

          <Text style={styles.label}>Confirm Password *</Text>
          <TextInput
            style={styles.input}
            value={form.confirmPassword}
            onChangeText={(v) => updateForm("confirmPassword", v)}
            secureTextEntry
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleRegister}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Create Account</Text>
            )}
          </TouchableOpacity>

          <View style={styles.footer}>
            <Text style={styles.footerText}>Already have an account? </Text>
            <TouchableOpacity onPress={() => navigation.navigate("Login")}>
              <Text style={styles.link}>Sign in</Text>
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
  header: { alignItems: "center", marginBottom: 24 },
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
  cardSubtitle: { fontSize: 14, color: "#6b7280", marginTop: 4, marginBottom: 16 },
  row: { flexDirection: "row", gap: 12 },
  halfField: { flex: 1 },
  label: {
    fontSize: 14,
    fontWeight: "500",
    color: "#374151",
    marginBottom: 6,
    marginTop: 12,
  },
  optional: { fontWeight: "400", color: "#9ca3af" },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: "#18181b",
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
  footer: { flexDirection: "row", justifyContent: "center", marginTop: 16 },
  footerText: { color: "#6b7280", fontSize: 14 },
  link: { color: "#18181b", fontSize: 14, fontWeight: "600" },
});
