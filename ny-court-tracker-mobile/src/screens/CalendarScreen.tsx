import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { dashboardApi, DashboardAppearance } from "../services/api";

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

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

export default function CalendarScreen({ navigation }: any) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [appearances, setAppearances] = useState<DashboardAppearance[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await dashboardApi.calendar({ month: month + 1, year });
      setAppearances(res.data);
    } catch (err) {
      console.error("Failed to fetch calendar", err);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [month, year])
  );

  const prevMonth = () => {
    if (month === 0) {
      setMonth(11);
      setYear(year - 1);
    } else {
      setMonth(month - 1);
    }
  };

  const nextMonth = () => {
    if (month === 11) {
      setMonth(0);
      setYear(year + 1);
    } else {
      setMonth(month + 1);
    }
  };

  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);

  // Group appearances by day
  const byDay: Record<number, DashboardAppearance[]> = {};
  appearances.forEach((app) => {
    const day = parseInt(app.appearance_date.split("-")[2]);
    if (!byDay[day]) byDay[day] = [];
    byDay[day].push(app);
  });

  const todayDate = today.getDate();
  const todayMonth = today.getMonth();
  const todayYear = today.getFullYear();

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Calendar</Text>
        <Text style={styles.subtitle}>View your court appearances</Text>
      </View>

      {/* Month Navigation */}
      <View style={styles.monthNav}>
        <TouchableOpacity onPress={prevMonth} style={styles.navButton}>
          <Ionicons name="chevron-back" size={22} color="#18181b" />
        </TouchableOpacity>
        <Text style={styles.monthText}>
          {MONTHS[month]} {year}
        </Text>
        <TouchableOpacity onPress={nextMonth} style={styles.navButton}>
          <Ionicons name="chevron-forward" size={22} color="#18181b" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#18181b" />
        </View>
      ) : (
        <>
          {/* Calendar Grid */}
          <View style={styles.calendarCard}>
            {/* Day headers */}
            <View style={styles.dayHeaders}>
              {DAYS.map((d) => (
                <Text key={d} style={styles.dayHeader}>
                  {d}
                </Text>
              ))}
            </View>

            {/* Calendar cells */}
            <View style={styles.calendarGrid}>
              {/* Empty cells before first day */}
              {Array.from({ length: firstDay }).map((_, i) => (
                <View key={`empty-${i}`} style={styles.calendarCell} />
              ))}
              {/* Day cells */}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const day = i + 1;
                const isToday =
                  day === todayDate && month === todayMonth && year === todayYear;
                const dayApps = byDay[day] || [];

                return (
                  <View
                    key={day}
                    style={[
                      styles.calendarCell,
                      isToday && styles.todayCell,
                    ]}
                  >
                    <Text
                      style={[
                        styles.dayNumber,
                        isToday && styles.todayNumber,
                      ]}
                    >
                      {day}
                    </Text>
                    <View style={styles.dots}>
                      {dayApps.slice(0, 3).map((app, idx) => (
                        <View
                          key={idx}
                          style={[
                            styles.dot,
                            {
                              backgroundColor:
                                COURT_COLORS[app.court_type] || "#6b7280",
                            },
                          ]}
                        />
                      ))}
                    </View>
                  </View>
                );
              })}
            </View>

            {/* Legend */}
            <View style={styles.legend}>
              {Object.entries(COURT_LABELS).map(([key, label]) => (
                <View key={key} style={styles.legendItem}>
                  <View
                    style={[
                      styles.legendDot,
                      { backgroundColor: COURT_COLORS[key] },
                    ]}
                  />
                  <Text style={styles.legendText}>{label}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* Appearances List */}
          <View style={styles.listSection}>
            <Text style={styles.listTitle}>
              Appearances This Month ({appearances.length})
            </Text>
            {appearances.length === 0 ? (
              <View style={styles.emptyState}>
                <Text style={styles.emptyText}>
                  No appearances this month
                </Text>
              </View>
            ) : (
              appearances.map((app) => (
                <TouchableOpacity
                  key={app.appearance_id}
                  style={styles.appCard}
                  onPress={() =>
                    navigation.navigate("CasesTab", {
                      screen: "CaseDetail",
                      params: { id: app.case_id },
                    })
                  }
                >
                  <View style={styles.appDateCol}>
                    <Text style={styles.appDay}>
                      {parseInt(app.appearance_date.split("-")[2])}
                    </Text>
                    <Text style={styles.appDayOfWeek}>
                      {new Date(app.appearance_date + "T00:00:00").toLocaleDateString(
                        "en-US",
                        { weekday: "short" }
                      )}
                    </Text>
                  </View>
                  <View style={styles.appInfo}>
                    <View style={styles.appInfoTop}>
                      <View
                        style={[
                          styles.courtBadge,
                          {
                            backgroundColor:
                              COURT_COLORS[app.court_type] || "#6b7280",
                          },
                        ]}
                      >
                        <Text style={styles.courtBadgeText}>
                          {COURT_LABELS[app.court_type]}
                        </Text>
                      </View>
                      <Text style={styles.appIndex}>{app.index_number}</Text>
                    </View>
                    <Text style={styles.appCounty}>
                      {app.county} County
                      {app.appearance_time ? ` at ${app.appearance_time}` : ""}
                    </Text>
                  </View>
                  {app.appearance_type && (
                    <Text style={styles.appType}>{app.appearance_type}</Text>
                  )}
                </TouchableOpacity>
              ))
            )}
          </View>
        </>
      )}

      <View style={{ height: 32 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  header: { padding: 20, paddingBottom: 8 },
  title: { fontSize: 24, fontWeight: "700", color: "#18181b" },
  subtitle: { fontSize: 14, color: "#6b7280", marginTop: 2 },
  monthNav: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  navButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#d1d5db",
    justifyContent: "center",
    alignItems: "center",
  },
  monthText: { fontSize: 18, fontWeight: "600", color: "#18181b" },
  loadingContainer: { paddingVertical: 60 },
  calendarCard: {
    backgroundColor: "#fff",
    marginHorizontal: 20,
    borderRadius: 12,
    padding: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  dayHeaders: { flexDirection: "row" },
  dayHeader: {
    flex: 1,
    textAlign: "center",
    fontSize: 12,
    fontWeight: "600",
    color: "#6b7280",
    paddingVertical: 8,
  },
  calendarGrid: { flexDirection: "row", flexWrap: "wrap" },
  calendarCell: {
    width: "14.28%",
    aspectRatio: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 2,
  },
  todayCell: {
    backgroundColor: "#18181b",
    borderRadius: 8,
  },
  dayNumber: { fontSize: 14, color: "#374151", fontWeight: "500" },
  todayNumber: { color: "#fff", fontWeight: "700" },
  dots: { flexDirection: "row", gap: 2, marginTop: 2 },
  dot: { width: 5, height: 5, borderRadius: 3 },
  legend: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: "#f3f4f6",
    marginTop: 8,
  },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 12, color: "#6b7280" },
  listSection: { paddingHorizontal: 20, marginTop: 20 },
  listTitle: { fontSize: 16, fontWeight: "600", color: "#18181b", marginBottom: 12 },
  emptyState: { alignItems: "center", paddingVertical: 24 },
  emptyText: { fontSize: 14, color: "#9ca3af" },
  appCard: {
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  appDateCol: { alignItems: "center", width: 44, marginRight: 12 },
  appDay: { fontSize: 20, fontWeight: "700", color: "#18181b" },
  appDayOfWeek: { fontSize: 11, color: "#6b7280" },
  appInfo: { flex: 1 },
  appInfoTop: { flexDirection: "row", alignItems: "center", gap: 6 },
  courtBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 3 },
  courtBadgeText: { color: "#fff", fontSize: 10, fontWeight: "600" },
  appIndex: { fontSize: 14, fontWeight: "600", color: "#18181b" },
  appCounty: { fontSize: 12, color: "#6b7280", marginTop: 2 },
  appType: { fontSize: 12, color: "#6b7280", marginLeft: 8 },
});
