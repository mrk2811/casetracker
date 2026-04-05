import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { discoveryApi, DiscoveredCase } from "../services/api";

const FILTER_OPTIONS = [
  { key: "pending", label: "Pending" },
  { key: "all", label: "All" },
  { key: "accepted", label: "Accepted" },
  { key: "dismissed", label: "Dismissed" },
];

const COURT_LABELS: Record<string, string> = {
  ny_webcivil: "NY WebCivil",
  ny_webcrimin: "NY WebCriminal",
};

export default function DiscoveriesScreen({ navigation }: any) {
  const [discoveries, setDiscoveries] = useState<DiscoveredCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeFilter, setActiveFilter] = useState("pending");
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [triggering, setTriggering] = useState(false);

  const fetchDiscoveries = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const params: { status?: string; limit?: number } = { limit: 50 };
      if (activeFilter !== "all") {
        params.status = activeFilter;
      }
      const res = await discoveryApi.list(params);
      setDiscoveries(res.data);
    } catch (err) {
      console.error("Failed to fetch discoveries", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchDiscoveries();
    }, [activeFilter])
  );

  const handleAccept = async (id: number) => {
    setActionLoading(id);
    try {
      const res = await discoveryApi.accept(id);
      Alert.alert("Case Added", res.data.message);
      fetchDiscoveries();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to accept case";
      Alert.alert("Error", msg);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDismiss = async (id: number) => {
    Alert.alert(
      "Dismiss Case",
      "Are you sure you don't want to track this case?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Dismiss",
          style: "destructive",
          onPress: async () => {
            setActionLoading(id);
            try {
              await discoveryApi.dismiss(id);
              fetchDiscoveries();
            } catch (err: any) {
              const msg = err?.response?.data?.detail || "Failed to dismiss";
              Alert.alert("Error", msg);
            } finally {
              setActionLoading(null);
            }
          },
        },
      ]
    );
  };

  const handleTriggerScan = async () => {
    setTriggering(true);
    try {
      const res = await discoveryApi.trigger();
      const { total_discoveries, errors } = res.data;
      if (total_discoveries > 0) {
        Alert.alert(
          "Scan Complete",
          `Found ${total_discoveries} new case${total_discoveries > 1 ? "s" : ""}!`
        );
      } else {
        Alert.alert("Scan Complete", "No new cases found.");
      }
      if (errors > 0) {
        console.warn("Discovery scan had errors:", errors);
      }
      fetchDiscoveries();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to run scan";
      Alert.alert("Error", msg);
    } finally {
      setTriggering(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatParties = (item: DiscoveredCase) => {
    if (item.plaintiff && item.defendant) {
      return `${item.plaintiff} v. ${item.defendant}`;
    }
    if (item.plaintiff) return item.plaintiff;
    if (item.defendant) return `Defendant: ${item.defendant}`;
    return "Parties unknown";
  };

  const renderDiscovery = ({ item }: { item: DiscoveredCase }) => {
    const isPending = item.status === "pending";
    const isAccepted = item.status === "accepted";
    const isDismissed = item.status === "dismissed";
    const isActioning = actionLoading === item.id;
    const courtLabel = COURT_LABELS[item.court_system || ""] || item.court_system || "Unknown";

    return (
      <View style={[styles.card, isPending && styles.pendingCard]}>
        {/* Status badge */}
        <View style={styles.cardTop}>
          <View
            style={[
              styles.statusBadge,
              isPending && styles.pendingBadge,
              isAccepted && styles.acceptedBadge,
              isDismissed && styles.dismissedBadge,
            ]}
          >
            <Ionicons
              name={
                isPending
                  ? "help-circle-outline"
                  : isAccepted
                  ? "checkmark-circle-outline"
                  : "close-circle-outline"
              }
              size={12}
              color={isPending ? "#f59e0b" : isAccepted ? "#22c55e" : "#9ca3af"}
            />
            <Text
              style={[
                styles.statusText,
                isPending && styles.pendingText,
                isAccepted && styles.acceptedText,
                isDismissed && styles.dismissedText,
              ]}
            >
              {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
            </Text>
          </View>
          <Text style={styles.dateText}>{formatDate(item.discovered_at)}</Text>
        </View>

        {/* Case info */}
        <Text style={styles.caseNumber}>Case #{item.index_number}</Text>
        <Text style={styles.parties} numberOfLines={2}>
          {formatParties(item)}
        </Text>

        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <Ionicons name="business-outline" size={14} color="#6b7280" />
            <Text style={styles.metaText}>{courtLabel}</Text>
          </View>
          {item.county && (
            <View style={styles.metaItem}>
              <Ionicons name="location-outline" size={14} color="#6b7280" />
              <Text style={styles.metaText}>{item.county}</Text>
            </View>
          )}
          <View style={styles.metaItem}>
            <Ionicons name="document-outline" size={14} color="#6b7280" />
            <Text style={styles.metaText}>
              {item.court_type === "criminal" ? "Criminal" : item.court_type === "local_civil" ? "Local Civil" : "Supreme"}
            </Text>
          </View>
        </View>

        {item.last_action && (
          <View style={styles.lastActionRow}>
            <Ionicons name="time-outline" size={14} color="#6b7280" />
            <Text style={styles.lastActionText} numberOfLines={1}>
              Last action: {item.last_action}
            </Text>
          </View>
        )}

        {/* Action buttons */}
        {isPending && (
          <View style={styles.actionRow}>
            <TouchableOpacity
              style={styles.acceptButton}
              onPress={() => handleAccept(item.id)}
              disabled={isActioning}
            >
              {isActioning ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Ionicons name="add-circle-outline" size={18} color="#fff" />
                  <Text style={styles.acceptButtonText}>Track This Case</Text>
                </>
              )}
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.dismissButton}
              onPress={() => handleDismiss(item.id)}
              disabled={isActioning}
            >
              <Ionicons name="close-outline" size={18} color="#6b7280" />
              <Text style={styles.dismissButtonText}>Dismiss</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    );
  }

  const pendingCount = discoveries.filter((d) => d.status === "pending").length;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Case Discovery</Text>
          <Text style={styles.subtitle}>
            {activeFilter === "pending"
              ? pendingCount > 0
                ? `${pendingCount} new case${pendingCount > 1 ? "s" : ""} found`
                : "No pending discoveries"
              : `${discoveries.length} result${discoveries.length !== 1 ? "s" : ""}`}
          </Text>
        </View>
        <TouchableOpacity
          style={styles.scanButton}
          onPress={handleTriggerScan}
          disabled={triggering}
        >
          {triggering ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Ionicons name="search-outline" size={18} color="#fff" />
          )}
        </TouchableOpacity>
      </View>

      {/* Filter chips */}
      <View style={styles.filterRow}>
        {FILTER_OPTIONS.map((opt) => (
          <TouchableOpacity
            key={opt.key}
            style={[
              styles.filterChip,
              activeFilter === opt.key && styles.filterChipActive,
            ]}
            onPress={() => setActiveFilter(opt.key)}
          >
            <Text
              style={[
                styles.filterChipText,
                activeFilter === opt.key && styles.filterChipTextActive,
              ]}
            >
              {opt.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {discoveries.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="search-outline" size={48} color="#d1d5db" />
          <Text style={styles.emptyTitle}>
            {activeFilter === "pending"
              ? "No New Cases Found"
              : "No Discoveries"}
          </Text>
          <Text style={styles.emptySubtitle}>
            {activeFilter === "pending"
              ? "We'll scan court systems weekly and notify you when new cases appear under your name."
              : "Try a different filter to see past discoveries."}
          </Text>
          {activeFilter === "pending" && (
            <TouchableOpacity
              style={styles.emptyButton}
              onPress={handleTriggerScan}
              disabled={triggering}
            >
              <Text style={styles.emptyButtonText}>
                {triggering ? "Scanning..." : "Scan Now"}
              </Text>
            </TouchableOpacity>
          )}
        </View>
      ) : (
        <FlatList
          data={discoveries}
          renderItem={renderDiscovery}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetchDiscoveries(true)}
            />
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
  scanButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#18181b",
    justifyContent: "center",
    alignItems: "center",
  },
  filterRow: {
    flexDirection: "row",
    paddingHorizontal: 20,
    paddingBottom: 8,
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "#f3f4f6",
  },
  filterChipActive: {
    backgroundColor: "#18181b",
  },
  filterChipText: {
    fontSize: 13,
    fontWeight: "500",
    color: "#6b7280",
  },
  filterChipTextActive: {
    color: "#fff",
  },
  listContent: { padding: 20, paddingTop: 8 },
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
  pendingCard: {
    borderWidth: 1,
    borderColor: "#fde68a",
    backgroundColor: "#fffbeb",
  },
  cardTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
    backgroundColor: "#f3f4f6",
  },
  pendingBadge: { backgroundColor: "#fef3c7" },
  acceptedBadge: { backgroundColor: "#dcfce7" },
  dismissedBadge: { backgroundColor: "#f3f4f6" },
  statusText: { fontSize: 12, fontWeight: "500", color: "#6b7280" },
  pendingText: { color: "#f59e0b" },
  acceptedText: { color: "#22c55e" },
  dismissedText: { color: "#9ca3af" },
  dateText: { fontSize: 12, color: "#9ca3af" },
  caseNumber: { fontSize: 17, fontWeight: "700", color: "#18181b", marginBottom: 4 },
  parties: { fontSize: 14, color: "#374151", marginBottom: 8, lineHeight: 20 },
  metaRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    marginBottom: 8,
  },
  metaItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  metaText: { fontSize: 12, color: "#6b7280" },
  lastActionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginBottom: 12,
    backgroundColor: "#f9fafb",
    padding: 8,
    borderRadius: 6,
  },
  lastActionText: { fontSize: 12, color: "#6b7280", flex: 1 },
  actionRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 4,
  },
  acceptButton: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "#18181b",
    paddingVertical: 10,
    borderRadius: 8,
  },
  acceptButtonText: { color: "#fff", fontSize: 14, fontWeight: "600" },
  dismissButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#fff",
  },
  dismissButtonText: { color: "#6b7280", fontSize: 14, fontWeight: "500" },
  emptyState: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: "#18181b", marginTop: 16 },
  emptySubtitle: {
    fontSize: 14,
    color: "#6b7280",
    marginTop: 8,
    textAlign: "center",
    lineHeight: 20,
  },
  emptyButton: {
    marginTop: 20,
    backgroundColor: "#18181b",
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  emptyButtonText: { color: "#fff", fontSize: 15, fontWeight: "600" },
});
