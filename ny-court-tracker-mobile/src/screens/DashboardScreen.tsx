import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { dashboardApi, DashboardAppearance, FreshnessInfo } from "../services/api";

const COURT_COLORS: Record<string, string> = {
  supreme: "#3b82f6",
  local_civil: "#10b981",
  criminal: "#ef4444",
};

const COURT_LABELS: Record<string, string> = {
  supreme: "Supreme",
  local_civil: "Local Civil",
  criminal: "Criminal",
};

const FRESHNESS_COLORS: Record<string, string> = {
  fresh: "#10b981",
  stale: "#f59e0b",
  outdated: "#ef4444",
  unknown: "#9ca3af",
};

const SOURCE_LABELS: Record<string, string> = {
  manual: "Manual",
  webcivil_scraper: "WebCivil Scraper",
  webcrimin_scraper: "WebCriminal Scraper",
  etrack_email: "Court Notification",
  api_provider: "API Provider",
};

function formatFreshness(freshness: FreshnessInfo | null): string {
  if (!freshness || freshness.status === "unknown") return "Not checked yet";
  const hours = freshness.hours_since_check;
  if (hours === null) return "Not checked yet";
  if (hours < 1) return "Just now";
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function getDayLabel(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffMs = date.getTime() - today.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays > 1 && diffDays <= 7) return `In ${diffDays} days`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function DashboardScreen({ navigation }: any) {
  const [appearances, setAppearances] = useState<DashboardAppearance[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filterPriority, setFilterPriority] = useState<string | null>(null);

  const fetchData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const params: any = { days_ahead: 90 };
      if (filterPriority) params.priority = filterPriority;
      const res = await dashboardApi.get(params);
      setAppearances(res.data);
    } catch (err) {
      console.error("Failed to fetch dashboard", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [filterPriority])
  );

  const todayStr = new Date().toISOString().split("T")[0];
  const weekEnd = new Date();
  weekEnd.setDate(weekEnd.getDate() + 7);
  const weekEndStr = weekEnd.toISOString().split("T")[0];

  const todayCount = appearances.filter((a) => a.appearance_date === todayStr).length;
  const weekCount = appearances.filter((a) => a.appearance_date <= weekEndStr).length;
  const highPriorityCount = appearances.filter((a) => a.priority === "high").length;

  // Group by date
  const grouped = appearances.reduce<Record<string, DashboardAppearance[]>>((acc, app) => {
    if (!acc[app.appearance_date]) acc[app.appearance_date] = [];
    acc[app.appearance_date].push(app);
    return acc;
  }, {});
  const sortedDates = Object.keys(grouped).sort();

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => fetchData(true)} />
      }
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Dashboard</Text>
          <Text style={styles.subtitle}>Your upcoming court appearances</Text>
        </View>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => navigation.navigate("CasesTab", { screen: "CaseForm" })}
        >
          <Ionicons name="add" size={20} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* Stats */}
      <View style={styles.statsRow}>
        <View style={[styles.statCard, { borderLeftColor: "#ef4444" }]}>
          <Text style={styles.statNumber}>{todayCount}</Text>
          <Text style={styles.statLabel}>Today</Text>
        </View>
        <View style={[styles.statCard, { borderLeftColor: "#f59e0b" }]}>
          <Text style={styles.statNumber}>{weekCount}</Text>
          <Text style={styles.statLabel}>This Week</Text>
        </View>
        <View style={[styles.statCard, { borderLeftColor: "#8b5cf6" }]}>
          <Text style={styles.statNumber}>{highPriorityCount}</Text>
          <Text style={styles.statLabel}>High Priority</Text>
        </View>
      </View>

      {/* Priority Filter */}
      <View style={styles.filterRow}>
        <TouchableOpacity
          style={[styles.filterChip, !filterPriority && styles.filterChipActive]}
          onPress={() => setFilterPriority(null)}
        >
          <Text style={[styles.filterChipText, !filterPriority && styles.filterChipTextActive]}>All</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterChip, filterPriority === "high" && styles.filterChipActive]}
          onPress={() => setFilterPriority(filterPriority === "high" ? null : "high")}
        >
          <Ionicons name="flag" size={12} color={filterPriority === "high" ? "#fff" : "#ef4444"} />
          <Text style={[styles.filterChipText, filterPriority === "high" && styles.filterChipTextActive]}>High Priority</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterChip, filterPriority === "normal" && styles.filterChipActive]}
          onPress={() => setFilterPriority(filterPriority === "normal" ? null : "normal")}
        >
          <Text style={[styles.filterChipText, filterPriority === "normal" && styles.filterChipTextActive]}>Normal</Text>
        </TouchableOpacity>
      </View>

      {/* Appearances */}
      {sortedDates.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="calendar-outline" size={48} color="#d1d5db" />
          <Text style={styles.emptyTitle}>No Upcoming Appearances</Text>
          <Text style={styles.emptySubtitle}>
            Add cases and their appearance dates to see them here.
          </Text>
          <TouchableOpacity
            style={styles.emptyButton}
            onPress={() => navigation.navigate("CasesTab", { screen: "CaseForm" })}
          >
            <Ionicons name="add" size={18} color="#18181b" />
            <Text style={styles.emptyButtonText}>Add Your First Case</Text>
          </TouchableOpacity>
        </View>
      ) : (
        sortedDates.map((date) => (
          <View key={date} style={styles.dateGroup}>
            <View style={styles.dateHeader}>
              <Text style={styles.dayLabel}>{getDayLabel(date)}</Text>
              <Text style={styles.dateText}>{formatDate(date)}</Text>
            </View>
            {grouped[date].map((app) => (
              <TouchableOpacity
                key={app.appearance_id}
                style={styles.appearanceCard}
                onPress={() =>
                  navigation.navigate("CasesTab", {
                    screen: "CaseDetail",
                    params: { id: app.case_id },
                  })
                }
              >
                <View style={styles.cardLeft}>
                  <View style={styles.badgeRow}>
                    <View
                      style={[
                        styles.courtBadge,
                        { backgroundColor: COURT_COLORS[app.court_type] || "#6b7280" },
                      ]}
                    >
                      <Text style={styles.courtBadgeText}>
                        {COURT_LABELS[app.court_type] || app.court_type}
                      </Text>
                    </View>
                    {app.priority === "high" && (
                      <View style={styles.priorityBadge}>
                        <Ionicons name="flag" size={10} color="#ef4444" />
                        <Text style={styles.priorityText}>HIGH</Text>
                      </View>
                    )}
                  </View>
                  <Text style={styles.caseIndex}>
                    {app.index_number}{" "}
                    <Text style={styles.countyText}>{app.county} County</Text>
                  </Text>
                  {(app.plaintiff || app.defendant) && (
                    <Text style={styles.partiesText} numberOfLines={1}>
                      {app.plaintiff} v. {app.defendant}
                    </Text>
                  )}
                  {/* Freshness Indicator */}
                  {app.freshness && (
                    <View style={styles.freshnessRow}>
                      <View
                        style={[
                          styles.freshnessDot,
                          { backgroundColor: FRESHNESS_COLORS[app.freshness.status] || "#9ca3af" },
                        ]}
                      />
                      <Text style={styles.freshnessText}>
                        {formatFreshness(app.freshness)}
                        {app.freshness.last_source
                          ? ` | ${SOURCE_LABELS[app.freshness.last_source] || app.freshness.last_source}`
                          : ""}
                      </Text>
                    </View>
                  )}
                </View>
                <View style={styles.cardRight}>
                  {app.appearance_time && (
                    <View style={styles.timeRow}>
                      <Ionicons name="time-outline" size={14} color="#6b7280" />
                      <Text style={styles.timeText}>{app.appearance_time}</Text>
                    </View>
                  )}
                  {app.location && (
                    <View style={styles.timeRow}>
                      <Ionicons name="location-outline" size={14} color="#6b7280" />
                      <Text style={styles.locationText} numberOfLines={1}>
                        {app.location}
                      </Text>
                    </View>
                  )}
                  {app.justice && (
                    <Text style={styles.justiceText}>
                      Justice {app.justice}
                      {app.part ? `, Part ${app.part}` : ""}
                    </Text>
                  )}
                </View>
              </TouchableOpacity>
            ))}
          </View>
        ))
      )}

      <View style={{ height: 32 }} />
    </ScrollView>
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
    backgroundColor: "#18181b",
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
  },
  statsRow: {
    flexDirection: "row",
    paddingHorizontal: 20,
    gap: 10,
    marginTop: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 14,
    borderLeftWidth: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  statNumber: { fontSize: 22, fontWeight: "700", color: "#18181b" },
  statLabel: { fontSize: 12, color: "#6b7280", marginTop: 2 },
  filterRow: {
    flexDirection: "row",
    paddingHorizontal: 20,
    gap: 8,
    marginTop: 12,
  },
  filterChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#fff",
  },
  filterChipActive: {
    backgroundColor: "#18181b",
    borderColor: "#18181b",
  },
  filterChipText: { fontSize: 12, fontWeight: "500", color: "#374151" },
  filterChipTextActive: { color: "#fff" },
  dateGroup: { marginTop: 20, paddingHorizontal: 20 },
  dateHeader: { flexDirection: "row", alignItems: "baseline", gap: 8, marginBottom: 8 },
  dayLabel: { fontSize: 15, fontWeight: "600", color: "#ef4444" },
  dateText: { fontSize: 13, color: "#6b7280" },
  appearanceCard: {
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 14,
    marginBottom: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  cardLeft: { flex: 1, marginRight: 12 },
  badgeRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 6 },
  courtBadge: {
    alignSelf: "flex-start",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  priorityBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    backgroundColor: "#fef2f2",
    borderWidth: 1,
    borderColor: "#fecaca",
  },
  priorityText: { fontSize: 10, fontWeight: "700", color: "#ef4444" },
  courtBadgeText: { color: "#fff", fontSize: 11, fontWeight: "600" },
  caseIndex: { fontSize: 15, fontWeight: "600", color: "#18181b" },
  countyText: { fontSize: 13, fontWeight: "400", color: "#6b7280" },
  partiesText: { fontSize: 13, color: "#6b7280", marginTop: 2 },
  freshnessRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 4,
  },
  freshnessDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  freshnessText: { fontSize: 11, color: "#9ca3af" },
  cardRight: { alignItems: "flex-end", justifyContent: "center" },
  timeRow: { flexDirection: "row", alignItems: "center", gap: 4, marginBottom: 2 },
  timeText: { fontSize: 13, color: "#6b7280" },
  locationText: { fontSize: 12, color: "#6b7280", maxWidth: 140 },
  justiceText: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  emptyState: {
    alignItems: "center",
    paddingVertical: 60,
    paddingHorizontal: 40,
  },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: "#18181b", marginTop: 16 },
  emptySubtitle: {
    fontSize: 14,
    color: "#6b7280",
    textAlign: "center",
    marginTop: 8,
  },
  emptyButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: 20,
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  emptyButtonText: { fontSize: 14, fontWeight: "500", color: "#18181b" },
});
