import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Modal,
  TextInput,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { casesApi, appearancesApi, Case, Appearance, FreshnessInfo } from "../services/api";

const FRESHNESS_COLORS: Record<string, string> = {
  fresh: "#10b981",
  stale: "#f59e0b",
  outdated: "#ef4444",
  unknown: "#9ca3af",
};

const SOURCE_LABELS: Record<string, string> = {
  manual: "Manual Entry",
  webcivil_scraper: "WebCivil Scraper",
  webcrimin_scraper: "WebCriminal Scraper",
  etrack_email: "Court Notification (eTrack)",
  api_provider: "API Provider",
};

const PRIORITY_LABELS: Record<string, string> = {
  normal: "Normal",
  high: "High Priority",
};

function formatFreshness(freshness: FreshnessInfo | null): string {
  if (!freshness || freshness.status === "unknown") return "Not checked yet";
  const hours = freshness.hours_since_check;
  if (hours === null) return "Not checked yet";
  if (hours < 1) return "Just now";
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

const COURT_LABELS: Record<string, string> = {
  supreme: "Supreme Court",
  local_civil: "Local Civil",
  criminal: "Criminal",
};

const COURT_COLORS: Record<string, string> = {
  supreme: "#3b82f6",
  local_civil: "#10b981",
  criminal: "#ef4444",
};

const STATUS_COLORS: Record<string, string> = {
  active: "#10b981",
  pending: "#f59e0b",
  disposed: "#6b7280",
};

export default function CaseDetailScreen({ route, navigation }: any) {
  const { id } = route.params;
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [appearances, setAppearances] = useState<Appearance[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [newApp, setNewApp] = useState({
    appearance_date: "",
    appearance_time: "",
    appearance_type: "",
    location: "",
    notes: "",
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [caseRes, appRes] = await Promise.all([
        casesApi.get(id),
        appearancesApi.list(id),
      ]);
      setCaseData(caseRes.data);
      setAppearances(appRes.data);
    } catch (err) {
      console.error("Failed to fetch case", err);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [id])
  );

  const handleDelete = () => {
    Alert.alert("Delete Case", "Are you sure you want to delete this case?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await casesApi.delete(id);
            navigation.goBack();
          } catch (err) {
            Alert.alert("Error", "Failed to delete case");
          }
        },
      },
    ]);
  };

  const handleAddAppearance = async () => {
    if (!newApp.appearance_date) {
      Alert.alert("Error", "Date is required");
      return;
    }
    setSaving(true);
    try {
      await appearancesApi.create(id, {
        appearance_date: newApp.appearance_date,
        appearance_time: newApp.appearance_time || undefined,
        appearance_type: newApp.appearance_type || undefined,
        location: newApp.location || undefined,
        notes: newApp.notes || undefined,
      } as Partial<Appearance>);
      setShowAddModal(false);
      setNewApp({ appearance_date: "", appearance_time: "", appearance_type: "", location: "", notes: "" });
      fetchData();
    } catch (err) {
      Alert.alert("Error", "Failed to add appearance");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAppearance = (appId: number) => {
    Alert.alert("Delete Appearance", "Remove this appearance?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await appearancesApi.delete(appId);
            fetchData();
          } catch (err) {
            Alert.alert("Error", "Failed to delete appearance");
          }
        },
      },
    ]);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    );
  }

  if (!caseData) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Case not found</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* Action buttons */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate("CaseForm", { id: caseData.id })}
        >
          <Ionicons name="create-outline" size={18} color="#18181b" />
          <Text style={styles.actionText}>Edit</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.deleteButton]}
          onPress={handleDelete}
        >
          <Ionicons name="trash-outline" size={18} color="#ef4444" />
          <Text style={[styles.actionText, { color: "#ef4444" }]}>Delete</Text>
        </TouchableOpacity>
      </View>

      {/* Case Info Card */}
      <View style={styles.card}>
        <View style={styles.badges}>
          <View
            style={[
              styles.courtBadge,
              { backgroundColor: COURT_COLORS[caseData.court_type] || "#6b7280" },
            ]}
          >
            <Text style={styles.badgeText}>
              {COURT_LABELS[caseData.court_type] || caseData.court_type}
            </Text>
          </View>
          <View
            style={[
              styles.statusBadge,
              { backgroundColor: (STATUS_COLORS[caseData.case_status] || "#6b7280") + "20" },
            ]}
          >
            <Text
              style={{
                fontSize: 11,
                fontWeight: "600",
                color: STATUS_COLORS[caseData.case_status] || "#6b7280",
              }}
            >
              {caseData.case_status}
            </Text>
          </View>
        </View>

        <Text style={styles.caseTitle}>
          {caseData.index_number}
          {caseData.case_year ? ` (${caseData.case_year})` : ""}
        </Text>

        <View style={styles.infoGrid}>
          <View style={styles.infoItem}>
            <Text style={styles.infoLabel}>County</Text>
            <Text style={styles.infoValue}>{caseData.county}</Text>
          </View>
          {caseData.justice && (
            <View style={styles.infoItem}>
              <Text style={styles.infoLabel}>Justice</Text>
              <Text style={styles.infoValue}>{caseData.justice}</Text>
            </View>
          )}
          {caseData.part && (
            <View style={styles.infoItem}>
              <Text style={styles.infoLabel}>Part</Text>
              <Text style={styles.infoValue}>{caseData.part}</Text>
            </View>
          )}
        </View>

        {(caseData.plaintiff || caseData.defendant) && (
          <>
            <View style={styles.divider} />
            <View style={styles.infoGrid}>
              {caseData.plaintiff && (
                <View style={styles.infoItem}>
                  <Text style={styles.infoLabel}>Plaintiff</Text>
                  <Text style={styles.infoValue}>{caseData.plaintiff}</Text>
                  {caseData.plaintiff_firm && (
                    <Text style={styles.firmText}>{caseData.plaintiff_firm}</Text>
                  )}
                </View>
              )}
              {caseData.defendant && (
                <View style={styles.infoItem}>
                  <Text style={styles.infoLabel}>Defendant</Text>
                  <Text style={styles.infoValue}>{caseData.defendant}</Text>
                  {caseData.defendant_firm && (
                    <Text style={styles.firmText}>{caseData.defendant_firm}</Text>
                  )}
                </View>
              )}
            </View>
          </>
        )}

        {caseData.notes && (
          <>
            <View style={styles.divider} />
            <Text style={styles.infoLabel}>Notes</Text>
            <Text style={styles.notesText}>{caseData.notes}</Text>
          </>
        )}
      </View>

      {/* Tracking Info Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Tracking Info</Text>
        <View style={styles.trackingGrid}>
          <View style={styles.trackingItem}>
            <Text style={styles.infoLabel}>Priority</Text>
            <View style={styles.priorityRow}>
              {caseData.priority === "high" && (
                <Ionicons name="flag" size={14} color="#ef4444" />
              )}
              <Text style={[
                styles.infoValue,
                caseData.priority === "high" && { color: "#ef4444", fontWeight: "700" },
              ]}>
                {PRIORITY_LABELS[caseData.priority] || caseData.priority}
              </Text>
            </View>
          </View>
          <View style={styles.trackingItem}>
            <Text style={styles.infoLabel}>Source</Text>
            <Text style={styles.infoValue}>
              {SOURCE_LABELS[caseData.source] || caseData.source}
            </Text>
          </View>
          <View style={styles.trackingItem}>
            <Text style={styles.infoLabel}>Verified</Text>
            <View style={styles.priorityRow}>
              <Ionicons
                name={caseData.verified ? "checkmark-circle" : "close-circle-outline"}
                size={16}
                color={caseData.verified ? "#10b981" : "#9ca3af"}
              />
              <Text style={styles.infoValue}>{caseData.verified ? "Yes" : "No"}</Text>
            </View>
          </View>
        </View>

        {/* Freshness Indicator */}
        {caseData.freshness && (
          <>
            <View style={styles.divider} />
            <View style={styles.freshnessBar}>
              <View
                style={[
                  styles.freshnessDot,
                  { backgroundColor: FRESHNESS_COLORS[caseData.freshness.status] || "#9ca3af" },
                ]}
              />
              <Text style={styles.freshnessLabel}>
                Last checked: {formatFreshness(caseData.freshness)}
              </Text>
              {caseData.freshness.last_source && (
                <Text style={styles.freshnessSource}>
                  Source: {SOURCE_LABELS[caseData.freshness.last_source] || caseData.freshness.last_source}
                </Text>
              )}
            </View>
          </>
        )}
      </View>

      {/* Appearances */}
      <View style={styles.card}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Scheduled Appearances</Text>
          <TouchableOpacity
            style={styles.addAppButton}
            onPress={() => setShowAddModal(true)}
          >
            <Ionicons name="add" size={16} color="#fff" />
            <Text style={styles.addAppText}>Add</Text>
          </TouchableOpacity>
        </View>

        {appearances.length === 0 ? (
          <View style={styles.emptyAppearances}>
            <Ionicons name="calendar-outline" size={32} color="#d1d5db" />
            <Text style={styles.emptyText}>No appearances scheduled</Text>
          </View>
        ) : (
          appearances.map((app) => {
            const isPast = new Date(app.appearance_date + "T23:59:59") < new Date();
            return (
              <View
                key={app.id}
                style={[styles.appearanceItem, isPast && styles.pastAppearance]}
              >
                <View style={styles.appLeft}>
                  <View style={styles.appDateRow}>
                    <Ionicons
                      name="calendar"
                      size={16}
                      color={isPast ? "#9ca3af" : "#18181b"}
                    />
                    <Text
                      style={[styles.appDate, isPast && styles.pastText]}
                    >
                      {new Date(app.appearance_date + "T00:00:00").toLocaleDateString("en-US", {
                        weekday: "short",
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </Text>
                    {isPast && (
                      <View style={styles.pastBadge}>
                        <Text style={styles.pastBadgeText}>Past</Text>
                      </View>
                    )}
                  </View>
                  <View style={styles.appDetails}>
                    {app.appearance_time && (
                      <View style={styles.detailRow}>
                        <Ionicons name="time-outline" size={14} color="#6b7280" />
                        <Text style={styles.detailText}>{app.appearance_time}</Text>
                      </View>
                    )}
                    {app.appearance_type && (
                      <Text style={styles.detailText}>{app.appearance_type}</Text>
                    )}
                    {app.location && (
                      <View style={styles.detailRow}>
                        <Ionicons name="location-outline" size={14} color="#6b7280" />
                        <Text style={styles.detailText}>{app.location}</Text>
                      </View>
                    )}
                    {app.notes && (
                      <Text style={styles.appNotes}>{app.notes}</Text>
                    )}
                  </View>
                </View>
                <TouchableOpacity
                  onPress={() => handleDeleteAppearance(app.id)}
                  style={styles.deleteAppButton}
                >
                  <Ionicons name="trash-outline" size={18} color="#9ca3af" />
                </TouchableOpacity>
              </View>
            );
          })
        )}
      </View>

      <View style={{ height: 32 }} />

      {/* Add Appearance Modal */}
      <Modal visible={showAddModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Appearance</Text>
              <TouchableOpacity onPress={() => setShowAddModal(false)}>
                <Ionicons name="close" size={24} color="#6b7280" />
              </TouchableOpacity>
            </View>

            <ScrollView>
              <Text style={styles.inputLabel}>Date * (YYYY-MM-DD)</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="2026-04-15"
                placeholderTextColor="#9ca3af"
                value={newApp.appearance_date}
                onChangeText={(v) => setNewApp({ ...newApp, appearance_date: v })}
              />

              <Text style={styles.inputLabel}>Time (HH:MM)</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="09:30"
                placeholderTextColor="#9ca3af"
                value={newApp.appearance_time}
                onChangeText={(v) => setNewApp({ ...newApp, appearance_time: v })}
              />

              <Text style={styles.inputLabel}>Type</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="e.g. Conference, Motion, Trial"
                placeholderTextColor="#9ca3af"
                value={newApp.appearance_type}
                onChangeText={(v) => setNewApp({ ...newApp, appearance_type: v })}
              />

              <Text style={styles.inputLabel}>Location</Text>
              <TextInput
                style={styles.modalInput}
                placeholder="Courtroom / Address"
                placeholderTextColor="#9ca3af"
                value={newApp.location}
                onChangeText={(v) => setNewApp({ ...newApp, location: v })}
              />

              <Text style={styles.inputLabel}>Notes</Text>
              <TextInput
                style={[styles.modalInput, { height: 60 }]}
                placeholder="Additional notes"
                placeholderTextColor="#9ca3af"
                value={newApp.notes}
                onChangeText={(v) => setNewApp({ ...newApp, notes: v })}
                multiline
              />

              <View style={styles.modalActions}>
                <TouchableOpacity
                  style={styles.saveButton}
                  onPress={handleAddAppearance}
                  disabled={saving}
                >
                  {saving ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.saveButtonText}>Add Appearance</Text>
                  )}
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.cancelButton}
                  onPress={() => setShowAddModal(false)}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb", padding: 20 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  errorText: { fontSize: 16, color: "#6b7280" },
  actions: { flexDirection: "row", justifyContent: "flex-end", gap: 8, marginBottom: 12 },
  actionButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#fff",
  },
  deleteButton: { borderColor: "#fecaca" },
  actionText: { fontSize: 14, fontWeight: "500", color: "#18181b" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  badges: { flexDirection: "row", gap: 6, marginBottom: 10 },
  courtBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "600" },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  caseTitle: { fontSize: 20, fontWeight: "700", color: "#18181b", marginBottom: 12 },
  infoGrid: { flexDirection: "row", flexWrap: "wrap", gap: 16 },
  infoItem: { minWidth: "40%" },
  infoLabel: { fontSize: 12, color: "#9ca3af", marginBottom: 2 },
  infoValue: { fontSize: 15, fontWeight: "500", color: "#18181b" },
  firmText: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  divider: { height: 1, backgroundColor: "#f3f4f6", marginVertical: 12 },
  notesText: { fontSize: 14, color: "#374151", marginTop: 4, lineHeight: 20 },
  trackingGrid: { flexDirection: "row", flexWrap: "wrap", gap: 16, marginTop: 8 },
  trackingItem: { minWidth: "28%" },
  priorityRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  freshnessBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    flexWrap: "wrap",
  },
  freshnessDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  freshnessLabel: { fontSize: 13, color: "#374151" },
  freshnessSource: { fontSize: 12, color: "#9ca3af" },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  sectionTitle: { fontSize: 17, fontWeight: "600", color: "#18181b" },
  addAppButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "#18181b",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
  },
  addAppText: { color: "#fff", fontSize: 13, fontWeight: "500" },
  emptyAppearances: { alignItems: "center", paddingVertical: 32 },
  emptyText: { fontSize: 14, color: "#9ca3af", marginTop: 8 },
  appearanceItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    marginBottom: 8,
  },
  pastAppearance: { backgroundColor: "#f9fafb", borderColor: "#e5e7eb" },
  appLeft: { flex: 1 },
  appDateRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  appDate: { fontSize: 14, fontWeight: "600", color: "#18181b" },
  pastText: { color: "#9ca3af" },
  pastBadge: { backgroundColor: "#f3f4f6", paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  pastBadgeText: { fontSize: 10, color: "#9ca3af" },
  appDetails: { marginTop: 6, gap: 2 },
  detailRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  detailText: { fontSize: 13, color: "#6b7280" },
  appNotes: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  deleteAppButton: { padding: 4 },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "flex-end",
  },
  modalContent: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    maxHeight: "80%",
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  modalTitle: { fontSize: 18, fontWeight: "600", color: "#18181b" },
  inputLabel: { fontSize: 14, fontWeight: "500", color: "#374151", marginBottom: 6, marginTop: 12 },
  modalInput: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: "#18181b",
  },
  modalActions: { marginTop: 24, gap: 10 },
  saveButton: {
    backgroundColor: "#18181b",
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
  },
  saveButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  cancelButton: {
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#d1d5db",
  },
  cancelButtonText: { color: "#6b7280", fontSize: 16 },
});
