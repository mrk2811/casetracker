import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { casesApi, Case } from "../services/api";

const COURT_COLORS: Record<string, string> = {
  supreme: "#3b82f6",
  local_civil: "#10b981",
  criminal: "#ef4444",
};

const COURT_LABELS: Record<string, string> = {
  supreme: "Supreme Court",
  local_civil: "Local Civil",
  criminal: "Criminal",
};

const STATUS_COLORS: Record<string, string> = {
  active: "#10b981",
  pending: "#f59e0b",
  disposed: "#6b7280",
};

export default function CasesScreen({ navigation }: any) {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchCases = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const res = await casesApi.list({ sort_by: "next_appearance" });
      setCases(res.data);
    } catch (err) {
      console.error("Failed to fetch cases", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchCases();
    }, [])
  );

  const renderCase = ({ item }: { item: Case }) => (
    <TouchableOpacity
      style={styles.caseCard}
      onPress={() => navigation.navigate("CaseDetail", { id: item.id })}
    >
      <View style={styles.cardTop}>
        <View style={styles.badges}>
          <View
            style={[
              styles.courtBadge,
              { backgroundColor: COURT_COLORS[item.court_type] || "#6b7280" },
            ]}
          >
            <Text style={styles.badgeText}>
              {COURT_LABELS[item.court_type] || item.court_type}
            </Text>
          </View>
          <View
            style={[
              styles.statusBadge,
              { backgroundColor: (STATUS_COLORS[item.case_status] || "#6b7280") + "20" },
            ]}
          >
            <Text
              style={[
                styles.statusText,
                { color: STATUS_COLORS[item.case_status] || "#6b7280" },
              ]}
            >
              {item.case_status}
            </Text>
          </View>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#d1d5db" />
      </View>

      <Text style={styles.indexNumber}>
        {item.index_number}
        {item.case_year ? ` (${item.case_year})` : ""}
      </Text>

      <Text style={styles.countyText}>{item.county} County</Text>

      {(item.plaintiff || item.defendant) && (
        <Text style={styles.partiesText} numberOfLines={1}>
          {item.plaintiff} v. {item.defendant}
        </Text>
      )}

      {item.justice && (
        <Text style={styles.justiceText}>
          Justice {item.justice}
          {item.part ? `, Part ${item.part}` : ""}
        </Text>
      )}

      {item.next_appearance && (
        <View style={styles.nextAppearance}>
          <Ionicons name="calendar-outline" size={14} color="#6b7280" />
          <Text style={styles.nextAppearanceText}>
            Next: {new Date(item.next_appearance + "T00:00:00").toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </Text>
        </View>
      )}
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>My Cases</Text>
          <Text style={styles.subtitle}>
            {cases.length} case{cases.length !== 1 ? "s" : ""} tracked
          </Text>
        </View>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => navigation.navigate("CaseForm")}
        >
          <Ionicons name="add" size={20} color="#fff" />
          <Text style={styles.addButtonText}>Add</Text>
        </TouchableOpacity>
      </View>

      {cases.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="folder-open-outline" size={48} color="#d1d5db" />
          <Text style={styles.emptyTitle}>No Cases Yet</Text>
          <Text style={styles.emptySubtitle}>
            Start by adding your first court case
          </Text>
          <TouchableOpacity
            style={styles.emptyButton}
            onPress={() => navigation.navigate("CaseForm")}
          >
            <Ionicons name="add" size={18} color="#fff" />
            <Text style={styles.emptyButtonText}>Add Case</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={cases}
          renderItem={renderCase}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => fetchCases(true)} />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 20,
    paddingBottom: 8,
  },
  title: { fontSize: 24, fontWeight: "700", color: "#18181b" },
  subtitle: { fontSize: 14, color: "#6b7280", marginTop: 2 },
  addButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#18181b",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 4,
  },
  addButtonText: { color: "#fff", fontSize: 14, fontWeight: "600" },
  listContent: { padding: 20, paddingTop: 8 },
  caseCard: {
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
  cardTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  badges: { flexDirection: "row", gap: 6 },
  courtBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "600" },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  statusText: { fontSize: 11, fontWeight: "600" },
  indexNumber: { fontSize: 17, fontWeight: "600", color: "#18181b" },
  countyText: { fontSize: 13, color: "#6b7280", marginTop: 2 },
  partiesText: { fontSize: 13, color: "#6b7280", marginTop: 4 },
  justiceText: { fontSize: 12, color: "#9ca3af", marginTop: 4 },
  nextAppearance: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: "#f3f4f6",
  },
  nextAppearanceText: { fontSize: 13, color: "#6b7280" },
  emptyState: { flex: 1, justifyContent: "center", alignItems: "center", padding: 40 },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: "#18181b", marginTop: 16 },
  emptySubtitle: { fontSize: 14, color: "#6b7280", marginTop: 8, textAlign: "center" },
  emptyButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: 20,
    backgroundColor: "#18181b",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  emptyButtonText: { color: "#fff", fontSize: 14, fontWeight: "600" },
});
