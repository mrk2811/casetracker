import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import {
  emailApi,
  EmailSetupGuide,
  EmailConfigResponse,
  EmailLogEntry,
} from "../services/api";
import * as Clipboard from "expo-clipboard";

export default function EmailSetupScreen({ navigation }: { navigation: any }) {
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<EmailConfigResponse | null>(null);
  const [guide, setGuide] = useState<EmailSetupGuide | null>(null);
  const [log, setLog] = useState<EmailLogEntry[]>([]);
  const [settingUp, setSettingUp] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [activeTab, setActiveTab] = useState<"setup" | "gmail" | "outlook" | "log">("setup");

  const fetchData = async () => {
    setLoading(true);
    try {
      // Try to get existing config
      try {
        const configRes = await emailApi.getConfig();
        setConfig(configRes.data);
      } catch {
        setConfig(null);
      }

      // Get setup guide
      try {
        const guideRes = await emailApi.getSetupGuide();
        setGuide(guideRes.data);
      } catch {
        // Guide not available yet
      }

      // Get email log
      try {
        const logRes = await emailApi.getLog(10);
        setLog(logRes.data);
      } catch {
        setLog([]);
      }
    } catch (err) {
      console.error("Failed to fetch email data", err);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [])
  );

  const handleSetup = async () => {
    setSettingUp(true);
    try {
      const res = await emailApi.setup();
      setConfig({
        id: 0,
        user_id: 0,
        inbound_email: res.data.inbound_email,
        forwarding_verified: res.data.forwarding_verified,
        provider: res.data.provider,
        created_at: new Date().toISOString(),
      });
      // Refresh guide with new email
      const guideRes = await emailApi.getSetupGuide();
      setGuide(guideRes.data);
      Alert.alert(
        "Email Set Up!",
        `Your unique forwarding address is:\n\n${res.data.inbound_email}\n\nFollow the setup steps to start receiving court notifications.`
      );
    } catch (err) {
      Alert.alert("Error", "Failed to set up email integration");
    } finally {
      setSettingUp(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const res = await emailApi.verify();
      if (res.data.verified) {
        Alert.alert("Verified!", "Email forwarding has been verified successfully.");
        fetchData();
      }
    } catch (err) {
      Alert.alert("Error", "Failed to verify email forwarding");
    } finally {
      setVerifying(false);
    }
  };

  const handleCopyEmail = async () => {
    if (config?.inbound_email) {
      await Clipboard.setStringAsync(config.inbound_email);
      Alert.alert("Copied!", "Email address copied to clipboard");
    }
  };

  const handleDisconnect = () => {
    Alert.alert(
      "Disconnect Email",
      "Are you sure you want to disconnect email integration? You will stop receiving court notification updates via email.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Disconnect",
          style: "destructive",
          onPress: async () => {
            try {
              await emailApi.deleteConfig();
              setConfig(null);
              setGuide(null);
              Alert.alert("Disconnected", "Email integration has been removed.");
            } catch {
              Alert.alert("Error", "Failed to disconnect email");
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
        >
          <Ionicons name="arrow-back" size={24} color="#18181b" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Email Integration</Text>
      </View>

      {/* Status Card */}
      <View style={styles.card}>
        <View style={styles.statusRow}>
          <Ionicons
            name={config ? "mail" : "mail-outline"}
            size={28}
            color={config?.forwarding_verified ? "#16a34a" : config ? "#f59e0b" : "#9ca3af"}
          />
          <View style={styles.statusInfo}>
            <Text style={styles.statusTitle}>
              {config?.forwarding_verified
                ? "Connected & Verified"
                : config
                ? "Set Up - Awaiting Verification"
                : "Not Connected"}
            </Text>
            <Text style={styles.statusDescription}>
              {config?.forwarding_verified
                ? "Receiving court notification emails"
                : config
                ? "Complete the setup steps below"
                : "Set up email forwarding to receive automatic court updates"}
            </Text>
          </View>
          <View
            style={[
              styles.statusDot,
              {
                backgroundColor: config?.forwarding_verified
                  ? "#16a34a"
                  : config
                  ? "#f59e0b"
                  : "#d1d5db",
              },
            ]}
          />
        </View>

        {config && (
          <View style={styles.emailBox}>
            <Text style={styles.emailLabel}>Your Forwarding Address</Text>
            <TouchableOpacity style={styles.emailRow} onPress={handleCopyEmail}>
              <Text style={styles.emailText} numberOfLines={1}>
                {config.inbound_email}
              </Text>
              <Ionicons name="copy-outline" size={18} color="#6b7280" />
            </TouchableOpacity>
            <Text style={styles.emailHint}>Tap to copy</Text>
          </View>
        )}

        {!config && (
          <TouchableOpacity
            style={styles.setupButton}
            onPress={handleSetup}
            disabled={settingUp}
          >
            {settingUp ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Ionicons name="mail-outline" size={20} color="#fff" />
                <Text style={styles.setupButtonText}>Set Up Email Integration</Text>
              </>
            )}
          </TouchableOpacity>
        )}

        {config && !config.forwarding_verified && (
          <TouchableOpacity
            style={styles.verifyButton}
            onPress={handleVerify}
            disabled={verifying}
          >
            {verifying ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Ionicons name="checkmark-circle-outline" size={20} color="#fff" />
                <Text style={styles.verifyButtonText}>Mark as Verified</Text>
              </>
            )}
          </TouchableOpacity>
        )}
      </View>

      {/* Privacy Notice */}
      <View style={styles.privacyCard}>
        <Ionicons name="shield-checkmark-outline" size={20} color="#16a34a" />
        <Text style={styles.privacyText}>
          {guide?.privacy_note ||
            "We only parse court notification emails. All other emails are automatically discarded without being read or stored."}
        </Text>
      </View>

      {/* Tab Selector */}
      {config && (
        <View style={styles.tabRow}>
          {(["setup", "gmail", "outlook", "log"] as const).map((tab) => (
            <TouchableOpacity
              key={tab}
              style={[styles.tab, activeTab === tab && styles.tabActive]}
              onPress={() => setActiveTab(tab)}
            >
              <Text
                style={[
                  styles.tabText,
                  activeTab === tab && styles.tabTextActive,
                ]}
              >
                {tab === "setup"
                  ? "Steps"
                  : tab === "gmail"
                  ? "Gmail"
                  : tab === "outlook"
                  ? "Outlook"
                  : "Activity"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Setup Steps */}
      {config && activeTab === "setup" && guide && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Setup Steps</Text>
          {guide.steps.map((step) => (
            <View key={step.step} style={styles.stepRow}>
              <View
                style={[
                  styles.stepCircle,
                  step.completed && styles.stepCircleCompleted,
                ]}
              >
                {step.completed ? (
                  <Ionicons name="checkmark" size={14} color="#fff" />
                ) : (
                  <Text style={styles.stepNumber}>{step.step}</Text>
                )}
              </View>
              <View style={styles.stepContent}>
                <Text style={styles.stepTitle}>{step.title}</Text>
                <Text style={styles.stepDescription}>{step.description}</Text>
                {step.url && (
                  <TouchableOpacity
                    style={styles.linkButton}
                    onPress={() => Linking.openURL(step.url!)}
                  >
                    <Text style={styles.linkButtonText}>Open Link</Text>
                    <Ionicons name="open-outline" size={14} color="#2563eb" />
                  </TouchableOpacity>
                )}
              </View>
            </View>
          ))}
        </View>
      )}

      {/* Gmail Instructions */}
      {config && activeTab === "gmail" && guide && (
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="logo-google" size={22} color="#ea4335" />
            <Text style={styles.cardTitle}>Gmail Setup</Text>
          </View>
          <Text style={styles.instructionText}>{guide.gmail_instructions}</Text>
        </View>
      )}

      {/* Outlook Instructions */}
      {config && activeTab === "outlook" && guide && (
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Ionicons name="logo-microsoft" size={22} color="#0078d4" />
            <Text style={styles.cardTitle}>Outlook Setup</Text>
          </View>
          <Text style={styles.instructionText}>{guide.outlook_instructions}</Text>
        </View>
      )}

      {/* Email Activity Log */}
      {config && activeTab === "log" && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Recent Email Activity</Text>
          {log.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="mail-unread-outline" size={40} color="#d1d5db" />
              <Text style={styles.emptyText}>
                No emails received yet. Forward a court notification to test.
              </Text>
            </View>
          ) : (
            log.map((entry) => (
              <View key={entry.id} style={styles.logEntry}>
                <View style={styles.logIcon}>
                  <Ionicons
                    name={
                      entry.events_extracted > 0
                        ? "checkmark-circle"
                        : "alert-circle"
                    }
                    size={20}
                    color={entry.events_extracted > 0 ? "#16a34a" : "#f59e0b"}
                  />
                </View>
                <View style={styles.logContent}>
                  <Text style={styles.logSubject} numberOfLines={1}>
                    {entry.subject || "No subject"}
                  </Text>
                  <Text style={styles.logMeta}>
                    {entry.events_extracted} event(s) extracted |{" "}
                    {new Date(entry.received_at).toLocaleDateString()}
                  </Text>
                </View>
              </View>
            ))
          )}
        </View>
      )}

      {/* Disconnect */}
      {config && (
        <TouchableOpacity
          style={styles.disconnectButton}
          onPress={handleDisconnect}
        >
          <Ionicons name="unlink-outline" size={18} color="#ef4444" />
          <Text style={styles.disconnectText}>Disconnect Email Integration</Text>
        </TouchableOpacity>
      )}

      {/* Explanation Card (shown when not set up) */}
      {!config && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>How It Works</Text>
          <View style={styles.howItWorksItem}>
            <View style={styles.howItWorksIcon}>
              <Ionicons name="mail-outline" size={24} color="#2563eb" />
            </View>
            <View style={styles.howItWorksContent}>
              <Text style={styles.howItWorksTitle}>1. Set Up Forwarding</Text>
              <Text style={styles.howItWorksDescription}>
                We give you a unique email address. Set up your email client to
                forward court notifications to this address.
              </Text>
            </View>
          </View>
          <View style={styles.howItWorksItem}>
            <View style={styles.howItWorksIcon}>
              <Ionicons name="scan-outline" size={24} color="#2563eb" />
            </View>
            <View style={styles.howItWorksContent}>
              <Text style={styles.howItWorksTitle}>2. Automatic Parsing</Text>
              <Text style={styles.howItWorksDescription}>
                We parse court notification emails to extract case updates,
                filings, and court dates automatically.
              </Text>
            </View>
          </View>
          <View style={styles.howItWorksItem}>
            <View style={styles.howItWorksIcon}>
              <Ionicons name="notifications-outline" size={24} color="#2563eb" />
            </View>
            <View style={styles.howItWorksContent}>
              <Text style={styles.howItWorksTitle}>3. Real-Time Updates</Text>
              <Text style={styles.howItWorksDescription}>
                Your dashboard updates instantly when court notifications arrive.
                Email data is treated as the most reliable source.
              </Text>
            </View>
          </View>
        </View>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: Platform.OS === "ios" ? 60 : 20,
    paddingBottom: 16,
    backgroundColor: "#fff",
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  backButton: { padding: 4, marginRight: 12 },
  headerTitle: { fontSize: 20, fontWeight: "700", color: "#18181b" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 16,
    marginTop: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  statusInfo: { flex: 1 },
  statusTitle: { fontSize: 16, fontWeight: "600", color: "#18181b" },
  statusDescription: { fontSize: 13, color: "#6b7280", marginTop: 2 },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  emailBox: {
    marginTop: 16,
    padding: 12,
    backgroundColor: "#f3f4f6",
    borderRadius: 8,
  },
  emailLabel: { fontSize: 11, color: "#6b7280", marginBottom: 4 },
  emailRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  emailText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#18181b",
    flex: 1,
    marginRight: 8,
  },
  emailHint: { fontSize: 11, color: "#9ca3af", marginTop: 4 },
  setupButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#2563eb",
    borderRadius: 10,
    paddingVertical: 14,
    marginTop: 16,
  },
  setupButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  verifyButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#16a34a",
    borderRadius: 10,
    paddingVertical: 12,
    marginTop: 12,
  },
  verifyButtonText: { color: "#fff", fontSize: 15, fontWeight: "600" },
  privacyCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    backgroundColor: "#f0fdf4",
    borderRadius: 10,
    padding: 14,
    marginHorizontal: 16,
    marginTop: 12,
    borderWidth: 1,
    borderColor: "#bbf7d0",
  },
  privacyText: { fontSize: 13, color: "#166534", flex: 1, lineHeight: 18 },
  tabRow: {
    flexDirection: "row",
    marginHorizontal: 16,
    marginTop: 16,
    backgroundColor: "#f3f4f6",
    borderRadius: 10,
    padding: 3,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: "center",
    borderRadius: 8,
  },
  tabActive: { backgroundColor: "#fff", shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 2, elevation: 1 },
  tabText: { fontSize: 13, color: "#6b7280", fontWeight: "500" },
  tabTextActive: { color: "#18181b", fontWeight: "600" },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 12,
  },
  cardTitle: { fontSize: 16, fontWeight: "600", color: "#18181b", marginBottom: 12 },
  stepRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 16,
  },
  stepCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "#e5e7eb",
    alignItems: "center",
    justifyContent: "center",
  },
  stepCircleCompleted: { backgroundColor: "#16a34a" },
  stepNumber: { fontSize: 13, fontWeight: "600", color: "#6b7280" },
  stepContent: { flex: 1 },
  stepTitle: { fontSize: 15, fontWeight: "600", color: "#18181b" },
  stepDescription: { fontSize: 13, color: "#6b7280", marginTop: 4, lineHeight: 18 },
  linkButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 8,
  },
  linkButtonText: { fontSize: 13, color: "#2563eb", fontWeight: "500" },
  instructionText: {
    fontSize: 14,
    color: "#374151",
    lineHeight: 22,
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 24,
    gap: 12,
  },
  emptyText: { fontSize: 14, color: "#9ca3af", textAlign: "center" },
  logEntry: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  logIcon: {},
  logContent: { flex: 1 },
  logSubject: { fontSize: 14, fontWeight: "500", color: "#18181b" },
  logMeta: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  disconnectButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginHorizontal: 16,
    marginTop: 16,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: "#fecaca",
    borderRadius: 10,
    backgroundColor: "#fff",
  },
  disconnectText: { fontSize: 14, fontWeight: "500", color: "#ef4444" },
  howItWorksItem: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 16,
  },
  howItWorksIcon: {
    width: 44,
    height: 44,
    borderRadius: 10,
    backgroundColor: "#eff6ff",
    alignItems: "center",
    justifyContent: "center",
  },
  howItWorksContent: { flex: 1 },
  howItWorksTitle: { fontSize: 15, fontWeight: "600", color: "#18181b" },
  howItWorksDescription: { fontSize: 13, color: "#6b7280", marginTop: 4, lineHeight: 18 },
});
