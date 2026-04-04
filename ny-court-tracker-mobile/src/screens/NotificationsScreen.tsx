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
import { notificationsApi, NotificationItem } from "../services/api";

const TYPE_ICONS: Record<string, string> = {
  reminder: "alarm-outline",
  case_update: "document-text-outline",
  system: "information-circle-outline",
};

export default function NotificationsScreen({ navigation }: any) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchNotifications = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const res = await notificationsApi.list();
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
    }, [])
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

  const unreadCount = notifications.filter((n) => !n.read).length;

  const renderNotification = ({ item }: { item: NotificationItem }) => {
    const iconName = TYPE_ICONS[item.type] || "notifications-outline";
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
      >
        <View
          style={[
            styles.iconContainer,
            !item.read && styles.unreadIcon,
          ]}
        >
          <Ionicons
            name={iconName as any}
            size={20}
            color={item.read ? "#9ca3af" : "#3b82f6"}
          />
        </View>
        <View style={styles.notifContent}>
          <View style={styles.notifHeader}>
            <Text style={[styles.notifTitle, !item.read && styles.unreadTitle]}>
              {item.title}
            </Text>
            {!item.read && <View style={styles.unreadDot} />}
          </View>
          <Text style={styles.notifMessage} numberOfLines={2}>
            {item.message}
          </Text>
          <Text style={styles.notifTime}>
            {new Date(item.created_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
            })}
          </Text>
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
        {unreadCount > 0 && (
          <TouchableOpacity
            style={styles.markAllButton}
            onPress={handleMarkAllRead}
          >
            <Ionicons name="checkmark-done" size={18} color="#3b82f6" />
            <Text style={styles.markAllText}>Mark all read</Text>
          </TouchableOpacity>
        )}
      </View>

      {notifications.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="notifications-off-outline" size={48} color="#d1d5db" />
          <Text style={styles.emptyTitle}>No Notifications</Text>
          <Text style={styles.emptySubtitle}>
            You'll see reminders and case updates here
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
  markAllButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#bfdbfe",
    backgroundColor: "#eff6ff",
  },
  markAllText: { fontSize: 13, color: "#3b82f6", fontWeight: "500" },
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
  },
  unreadIcon: { backgroundColor: "#dbeafe" },
  notifContent: { flex: 1 },
  notifHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  notifTitle: { fontSize: 15, fontWeight: "500", color: "#374151", flex: 1 },
  unreadTitle: { fontWeight: "600", color: "#18181b" },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#3b82f6",
    marginLeft: 8,
  },
  notifMessage: { fontSize: 13, color: "#6b7280", marginTop: 4, lineHeight: 18 },
  notifTime: { fontSize: 12, color: "#9ca3af", marginTop: 4 },
  emptyState: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: "#18181b", marginTop: 16 },
  emptySubtitle: { fontSize: 14, color: "#6b7280", marginTop: 8, textAlign: "center" },
});
