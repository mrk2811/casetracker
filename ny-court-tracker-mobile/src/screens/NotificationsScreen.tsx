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
import { notificationsApi, NotificationItem } from "../services/api";

const TYPE_ICONS: Record<string, string> = {
  reminder: "alarm-outline",
  update: "document-text-outline",
  system: "information-circle-outline",
};

const TYPE_COLORS: Record<string, string> = {
  reminder: "#f59e0b",
  update: "#3b82f6",
  system: "#6b7280",
};

const FILTER_OPTIONS = [
  { key: "all", label: "All" },
  { key: "unread", label: "Unread" },
  { key: "reminder", label: "Reminders" },
  { key: "update", label: "Updates" },
  { key: "system", label: "System" },
];

export default function NotificationsScreen({ navigation }: any) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeFilter, setActiveFilter] = useState("all");

  const fetchNotifications = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const params: Record<string, unknown> = {};
      if (activeFilter === "unread") {
        params.unread_only = true;
      } else if (activeFilter !== "all") {
        params.notification_type = activeFilter;
      }
      const res = await notificationsApi.list(params as { notification_type?: string; unread_only?: boolean });
      setNotifications(res.data);
    } catch (err) {
      console.error("Failed to fetch notifications", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchNotifications();
    }, [activeFilter])
  );

  const handleMarkRead = async (id: number) => {
    try {
      await notificationsApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch (err) {
      console.error("Failed to mark as read", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch (err) {
      console.error("Failed to mark all as read", err);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await notificationsApi.deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      console.error("Failed to delete notification", err);
    }
  };

  const handleClearAll = () => {
    Alert.alert(
      "Clear All Notifications",
      "Are you sure you want to delete all notifications?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Clear All",
          style: "destructive",
          onPress: async () => {
            try {
              await notificationsApi.clearAll();
              setNotifications([]);
            } catch (err) {
              console.error("Failed to clear notifications", err);
            }
          },
        },
      ]
    );
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    const diffHrs = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHrs < 24) return `${diffHrs}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  const renderNotification = ({ item }: { item: NotificationItem }) => {
    const iconName = TYPE_ICONS[item.type] || "notifications-outline";
    const iconColor = TYPE_COLORS[item.type] || "#6b7280";
    return (
      <TouchableOpacity
        style={[styles.notifCard, !item.read && styles.unreadCard]}
        onPress={() => {
          if (!item.read) handleMarkRead(item.id);
          if (item.case_id) {
            navigation.navigate("CasesTab", {
              screen: "CaseDetail",
              params: { id: item.case_id },
            });
          }
        }}
        onLongPress={() => {
          Alert.alert("Notification", "What would you like to do?", [
            { text: "Cancel", style: "cancel" },
            !item.read
              ? { text: "Mark as Read", onPress: () => handleMarkRead(item.id) }
              : { text: "OK", style: "cancel" },
            { text: "Delete", style: "destructive", onPress: () => handleDelete(item.id) },
          ]);
        }}
      >
        <View
          style={[
            styles.iconContainer,
            !item.read && styles.unreadIcon,
            { borderColor: iconColor + "30" },
          ]}
        >
          <Ionicons
            name={iconName as any}
            size={20}
            color={item.read ? "#9ca3af" : iconColor}
          />
        </View>
        <View style={styles.notifContent}>
          <View style={styles.notifHeader}>
            <Text style={[styles.notifTitle, !item.read && styles.unreadTitle]} numberOfLines={1}>
              {item.title}
            </Text>
            <View style={styles.notifMeta}>
              {item.push_sent && (
                <Ionicons name="phone-portrait-outline" size={12} color="#9ca3af" style={{ marginRight: 4 }} />
              )}
              {!item.read && <View style={styles.unreadDot} />}
            </View>
          </View>
          <Text style={styles.notifMessage} numberOfLines={2}>
            {item.message}
          </Text>
          <View style={styles.notifFooter}>
            <Text style={styles.notifTime}>{formatTime(item.created_at)}</Text>
            <View style={[styles.typeBadge, { backgroundColor: iconColor + "15" }]}>
              <Text style={[styles.typeBadgeText, { color: iconColor }]}>
                {item.type}
              </Text>
            </View>
          </View>
        </View>
      </TouchableOpacity>
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
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Notifications</Text>
          <Text style={styles.subtitle}>
            {unreadCount > 0 ? `${unreadCount} unread` : "All caught up"}
          </Text>
        </View>
        <View style={styles.headerActions}>
          {unreadCount > 0 && (
            <TouchableOpacity
              style={styles.markAllButton}
              onPress={handleMarkAllRead}
            >
              <Ionicons name="checkmark-done" size={16} color="#3b82f6" />
            </TouchableOpacity>
          )}
          {notifications.length > 0 && (
            <TouchableOpacity
              style={styles.clearButton}
              onPress={handleClearAll}
            >
              <Ionicons name="trash-outline" size={16} color="#ef4444" />
            </TouchableOpacity>
          )}
        </View>
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

      {notifications.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="notifications-off-outline" size={48} color="#d1d5db" />
          <Text style={styles.emptyTitle}>
            {activeFilter !== "all" ? "No Matching Notifications" : "No Notifications"}
          </Text>
          <Text style={styles.emptySubtitle}>
            {activeFilter !== "all"
              ? "Try a different filter"
              : "You'll see reminders, case updates, and alerts here"}
          </Text>
        </View>
      ) : (
        <FlatList
          data={notifications}
          renderItem={renderNotification}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetchNotifications(true)}
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
  headerActions: {
    flexDirection: "row",
    gap: 8,
  },
  markAllButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#bfdbfe",
    backgroundColor: "#eff6ff",
  },
  clearButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#fecaca",
    backgroundColor: "#fef2f2",
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
  notifCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    flexDirection: "row",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  unreadCard: { backgroundColor: "#f0f9ff", borderWidth: 1, borderColor: "#bfdbfe" },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#f3f4f6",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
    borderWidth: 1,
    borderColor: "#e5e7eb",
  },
  unreadIcon: { backgroundColor: "#dbeafe" },
  notifContent: { flex: 1 },
  notifHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  notifMeta: {
    flexDirection: "row",
    alignItems: "center",
  },
  notifTitle: { fontSize: 15, fontWeight: "500", color: "#374151", flex: 1 },
  unreadTitle: { fontWeight: "600", color: "#18181b" },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#3b82f6",
    marginLeft: 4,
  },
  notifMessage: { fontSize: 13, color: "#6b7280", marginTop: 4, lineHeight: 18 },
  notifFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 6,
  },
  notifTime: { fontSize: 12, color: "#9ca3af" },
  typeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  typeBadgeText: {
    fontSize: 11,
    fontWeight: "500",
    textTransform: "capitalize",
  },
  emptyState: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: "#18181b", marginTop: 16 },
  emptySubtitle: { fontSize: 14, color: "#6b7280", marginTop: 8, textAlign: "center" },
});
