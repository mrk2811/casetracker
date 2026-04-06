import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  ActivityIndicator,
  Alert,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useNavigation } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import { notificationsApi, NotificationSettings, emailApi, discoveryApi, DiscoverySettings } from "../services/api";

const REMINDER_OPTIONS = [
  { value: 1, label: "1 day before" },
  { value: 7, label: "7 days before" },
  { value: 15, label: "15 days before" },
  { value: 30, label: "30 days before" },
];

const DIGEST_OPTIONS = [
  { value: "off", label: "Off" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
];

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const navigation = useNavigation<any>();
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showReminderPicker, setShowReminderPicker] = useState(false);
  const [showDigestPicker, setShowDigestPicker] = useState(false);
  const [emailStatus, setEmailStatus] = useState<{ configured: boolean; verified: boolean } | null>(null);
  const [discoverySettings, setDiscoverySettings] = useState<DiscoverySettings | null>(null);
  const [savingDiscovery, setSavingDiscovery] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await notificationsApi.getSettings();
      setSettings(res.data);
    } catch (err) {
      console.error("Failed to fetch settings", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchEmailStatus = async () => {
    try {
      const res = await emailApi.getConfig();
      setEmailStatus({ configured: true, verified: res.data.forwarding_verified });
    } catch {
      setEmailStatus({ configured: false, verified: false });
    }
  };

  const fetchDiscoverySettings = async () => {
    try {
      const res = await discoveryApi.getSettings();
      setDiscoverySettings(res.data);
    } catch {
      // Not configured yet
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchSettings();
      fetchEmailStatus();
      fetchDiscoverySettings();
    }, [])
  );

  const saveDiscoverySettings = async (updated: Partial<DiscoverySettings>) => {
    if (!discoverySettings) return;
    const newSettings = { ...discoverySettings, ...updated };
    setDiscoverySettings(newSettings);
    setSavingDiscovery(true);
    try {
      await discoveryApi.updateSettings(updated);
    } catch {
      Alert.alert("Error", "Failed to save discovery settings");
      fetchDiscoverySettings();
    } finally {
      setSavingDiscovery(false);
    }
  };

  const saveSettings = async (updated: Partial<NotificationSettings>) => {
    if (!settings) return;
    const newSettings = { ...settings, ...updated };
    setSettings(newSettings);
    setSaving(true);
    try {
      await notificationsApi.updateSettings(updated);
    } catch (err) {
      Alert.alert("Error", "Failed to save settings");
      fetchSettings();
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    if (Platform.OS === "web") {
      setShowLogoutConfirm(true);
    } else {
      Alert.alert("Sign Out", "Are you sure you want to sign out?", [
        { text: "Cancel", style: "cancel" },
        { text: "Sign Out", style: "destructive", onPress: logout },
      ]);
    }
  };

  const confirmLogout = () => {
    setShowLogoutConfirm(false);
    logout();
  };

  const cancelLogout = () => {
    setShowLogoutConfirm(false);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    );
  }

  const selectedReminder = REMINDER_OPTIONS.find(
    (r) => r.value === settings?.reminder_days
  );

  const selectedDigest = DIGEST_OPTIONS.find(
    (d) => d.value === settings?.digest_frequency
  );

  return (
    <ScrollView style={styles.container}>
      {/* Account Info */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="person-outline" size={22} color="#18181b" />
          <Text style={styles.cardTitle}>Account Information</Text>
        </View>

        <View style={styles.infoGrid}>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>Name</Text>
            <Text style={styles.infoValue}>
              {user?.first_name} {user?.last_name}
            </Text>
          </View>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>Email</Text>
            <Text style={styles.infoValue}>{user?.email}</Text>
          </View>
          {user?.attorney_reg_number && (
            <View style={styles.infoItem}>
              <Text style={styles.infoLabel}>Attorney Reg #</Text>
              <Text style={styles.infoValue}>{user.attorney_reg_number}</Text>
            </View>
          )}
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>Member Since</Text>
            <Text style={styles.infoValue}>
              {user?.created_at
                ? new Date(user.created_at).toLocaleDateString()
                : "—"}
            </Text>
          </View>
        </View>
      </View>

      {/* Push Notifications */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="phone-portrait-outline" size={22} color="#18181b" />
          <Text style={styles.cardTitle}>Push Notifications</Text>
          {saving && <ActivityIndicator size="small" color="#6b7280" style={{ marginLeft: 8 }} />}
        </View>

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Push Notifications</Text>
            <Text style={styles.settingDescription}>
              Receive push alerts on this device
            </Text>
          </View>
          <Switch
            value={settings?.push_enabled ?? true}
            onValueChange={(v) => saveSettings({ push_enabled: v })}
            trackColor={{ false: "#d1d5db", true: "#18181b" }}
            thumbColor="#fff"
          />
        </View>

        <View style={styles.divider} />

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Case Updates</Text>
            <Text style={styles.settingDescription}>
              Get notified when case details change
            </Text>
          </View>
          <Switch
            value={settings?.case_updates_enabled ?? false}
            onValueChange={(v) => saveSettings({ case_updates_enabled: v })}
            trackColor={{ false: "#d1d5db", true: "#18181b" }}
            thumbColor="#fff"
          />
        </View>

        <View style={styles.divider} />

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Appearance Reminders</Text>
            <Text style={styles.settingDescription}>
              How far in advance to send reminders
            </Text>
          </View>
          <TouchableOpacity
            style={styles.reminderPicker}
            onPress={() => setShowReminderPicker(!showReminderPicker)}
          >
            <Text style={styles.reminderText}>
              {selectedReminder?.label || "1 day before"}
            </Text>
            <Ionicons name="chevron-down" size={16} color="#6b7280" />
          </TouchableOpacity>
        </View>
        {showReminderPicker && (
          <View style={styles.pickerOptions}>
            {REMINDER_OPTIONS.map((opt) => (
              <TouchableOpacity
                key={opt.value}
                style={[
                  styles.pickerOption,
                  settings?.reminder_days === opt.value &&
                    styles.pickerOptionSelected,
                ]}
                onPress={() => {
                  saveSettings({ reminder_days: opt.value });
                  setShowReminderPicker(false);
                }}
              >
                <Text
                  style={[
                    styles.pickerOptionText,
                    settings?.reminder_days === opt.value &&
                      styles.pickerOptionTextSelected,
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>

      {/* Email & Digest */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="mail-outline" size={22} color="#18181b" />
          <Text style={styles.cardTitle}>Email & Digest</Text>
        </View>

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Email Notifications</Text>
            <Text style={styles.settingDescription}>
              Receive email alerts for your cases
            </Text>
          </View>
          <Switch
            value={settings?.email_enabled ?? false}
            onValueChange={(v) => saveSettings({ email_enabled: v })}
            trackColor={{ false: "#d1d5db", true: "#18181b" }}
            thumbColor="#fff"
          />
        </View>

        <View style={styles.divider} />

        <View style={styles.settingRow}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Digest Summary</Text>
            <Text style={styles.settingDescription}>
              Receive a summary of case activity
            </Text>
          </View>
          <TouchableOpacity
            style={styles.reminderPicker}
            onPress={() => setShowDigestPicker(!showDigestPicker)}
          >
            <Text style={styles.reminderText}>
              {selectedDigest?.label || "Off"}
            </Text>
            <Ionicons name="chevron-down" size={16} color="#6b7280" />
          </TouchableOpacity>
        </View>
        {showDigestPicker && (
          <View style={styles.pickerOptions}>
            {DIGEST_OPTIONS.map((opt) => (
              <TouchableOpacity
                key={opt.value}
                style={[
                  styles.pickerOption,
                  settings?.digest_frequency === opt.value &&
                    styles.pickerOptionSelected,
                ]}
                onPress={() => {
                  saveSettings({ digest_frequency: opt.value });
                  setShowDigestPicker(false);
                }}
              >
                <Text
                  style={[
                    styles.pickerOptionText,
                    settings?.digest_frequency === opt.value &&
                      styles.pickerOptionTextSelected,
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        <View style={styles.divider} />

        {/* Email Integration Status */}
        <Text style={styles.settingLabel}>Court Email Integration</Text>
        <Text style={[styles.settingDescription, { marginBottom: 8 }]}>
          Forward eTrack notifications for automatic case updates
        </Text>
        <View style={styles.emailStatusRow}>
          <View style={[styles.emailStatusDot, { backgroundColor: emailStatus?.configured ? (emailStatus?.verified ? '#22c55e' : '#f59e0b') : '#d1d5db' }]} />
          <Text style={styles.emailStatusText}>
            {emailStatus?.configured
              ? emailStatus?.verified
                ? 'Connected & Verified'
                : 'Set Up - Awaiting Verification'
              : 'Not Connected'}
          </Text>
        </View>
        <TouchableOpacity
          style={styles.emailSetupButton}
          onPress={() => navigation.navigate('EmailSetup')}
        >
          <Ionicons name="settings-outline" size={18} color="#fff" />
          <Text style={styles.emailSetupButtonText}>
            {emailStatus?.configured ? 'Manage Email Integration' : 'Set Up Email Integration'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Case Discovery */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="search-outline" size={22} color="#18181b" />
          <Text style={styles.cardTitle}>Weekly Case Discovery</Text>
          {savingDiscovery && <ActivityIndicator size="small" color="#6b7280" style={{ marginLeft: 8 }} />}
        </View>

        <Text style={styles.settingDescription}>
          Automatically scan court systems weekly to find new cases under your name.
        </Text>

        <View style={[styles.settingRow, { marginTop: 12 }]}>
          <View style={styles.settingInfo}>
            <Text style={styles.settingLabel}>Enable Discovery</Text>
            <Text style={styles.settingDescription}>
              Scan every Monday at 7am ET
            </Text>
          </View>
          <Switch
            value={discoverySettings?.enabled ?? true}
            onValueChange={(v) => saveDiscoverySettings({ enabled: v })}
            trackColor={{ false: "#d1d5db", true: "#18181b" }}
            thumbColor="#fff"
          />
        </View>

        <View style={styles.divider} />

        <View style={styles.infoItem}>
          <Text style={styles.infoLabel}>Attorney Name</Text>
          <Text style={styles.infoValue}>
            {discoverySettings?.attorney_name || "Not set"}
          </Text>
        </View>

        {discoverySettings?.attorney_reg_number && (
          <View style={[styles.infoItem, { marginTop: 8 }]}>
            <Text style={styles.infoLabel}>Registration #</Text>
            <Text style={styles.infoValue}>
              {discoverySettings.attorney_reg_number}
            </Text>
          </View>
        )}

        <View style={[styles.infoItem, { marginTop: 8 }]}>
          <Text style={styles.infoLabel}>Courts Searched</Text>
          <Text style={styles.infoValue}>
            {(discoverySettings?.search_courts || "ny_webcivil,ny_webcrimin")
              .split(",")
              .map((c: string) => c.trim().replace("ny_", "NY ").replace("webcivil", "WebCivil").replace("webcrimin", "WebCriminal"))
              .join(", ")}
          </Text>
        </View>

        {discoverySettings?.last_run_at && (
          <View style={[styles.infoItem, { marginTop: 8 }]}>
            <Text style={styles.infoLabel}>Last Scan</Text>
            <Text style={styles.infoValue}>
              {new Date(discoverySettings.last_run_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </Text>
          </View>
        )}

        <TouchableOpacity
          style={styles.discoveryButton}
          onPress={() => navigation.navigate('Discoveries')}
        >
          <Ionicons name="search-outline" size={18} color="#fff" />
          <Text style={styles.discoveryButtonText}>View Discovered Cases</Text>
        </TouchableOpacity>
      </View>

      {/* Sign Out */}
      {showLogoutConfirm ? (
        <View style={styles.logoutConfirmCard}>
          <Text style={styles.logoutConfirmTitle}>Sign Out</Text>
          <Text style={styles.logoutConfirmMessage}>Are you sure you want to sign out?</Text>
          <View style={styles.logoutConfirmButtons}>
            <TouchableOpacity style={styles.logoutCancelBtn} onPress={cancelLogout}>
              <Text style={styles.logoutCancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.logoutConfirmBtn} onPress={confirmLogout}>
              <Text style={styles.logoutConfirmBtnText}>Sign Out</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <TouchableOpacity style={styles.signOutButton} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={20} color="#ef4444" />
          <Text style={styles.signOutText}>Sign Out</Text>
        </TouchableOpacity>
      )}

      <View style={{ height: 40 }} />

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb", padding: 20 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 16,
  },
  cardTitle: { fontSize: 17, fontWeight: "600", color: "#18181b" },
  infoGrid: { gap: 12 },
  infoItem: {},
  infoLabel: { fontSize: 12, color: "#9ca3af", marginBottom: 2 },
  infoValue: { fontSize: 15, fontWeight: "500", color: "#18181b" },
  settingRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 4,
  },
  settingInfo: { flex: 1, marginRight: 12 },
  settingLabel: { fontSize: 15, fontWeight: "500", color: "#18181b" },
  settingDescription: { fontSize: 13, color: "#6b7280", marginTop: 2 },
  divider: { height: 1, backgroundColor: "#f3f4f6", marginVertical: 12 },
  reminderPicker: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 6,
  },
  reminderText: { fontSize: 13, color: "#374151" },
  pickerOptions: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    marginTop: 8,
    overflow: "hidden",
  },
  pickerOption: {
    padding: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  pickerOptionSelected: { backgroundColor: "#f3f4f6" },
  pickerOptionText: { fontSize: 14, color: "#374151" },
  pickerOptionTextSelected: { fontWeight: "600", color: "#18181b" },
  signOutButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: "#fecaca",
    borderRadius: 10,
    backgroundColor: "#fff",
  },
  signOutText: { fontSize: 16, fontWeight: "500", color: "#ef4444" },
  emailStatusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 12,
    marginBottom: 12,
  },
  emailStatusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  emailStatusText: {
    fontSize: 14,
    fontWeight: "500",
    color: "#374151",
  },
  emailSetupButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#18181b",
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 4,
  },
  emailSetupButtonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
  },
  discoveryButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#18181b",
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
  },
  discoveryButtonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
  },
  logoutConfirmCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: "#fecaca",
    alignItems: "center",
  },
  logoutConfirmTitle: {
    fontSize: 17,
    fontWeight: "600",
    color: "#18181b",
    marginBottom: 6,
  },
  logoutConfirmMessage: {
    fontSize: 14,
    color: "#6b7280",
    marginBottom: 16,
  },
  logoutConfirmButtons: {
    flexDirection: "row",
    gap: 12,
    width: "100%",
  },
  logoutCancelBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d1d5db",
    alignItems: "center",
  },
  logoutCancelText: {
    fontSize: 15,
    fontWeight: "500",
    color: "#374151",
  },
  logoutConfirmBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: "#ef4444",
    alignItems: "center",
  },
  logoutConfirmBtnText: {
    fontSize: 15,
    fontWeight: "600",
    color: "#fff",
  },
});
