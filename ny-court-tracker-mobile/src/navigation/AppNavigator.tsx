import React, { useEffect, useState, useCallback, useRef } from "react";
import { ActivityIndicator, View, Text, StyleSheet } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../context/AuthContext";
import { notificationsApi, discoveryApi } from "../services/api";
import { registerForPushNotifications, setupNotificationResponseListener } from "../services/pushNotifications";

import LoginScreen from "../screens/LoginScreen";
import RegisterScreen from "../screens/RegisterScreen";
import ForgotPasswordScreen from "../screens/ForgotPasswordScreen";
import ResetPasswordScreen from "../screens/ResetPasswordScreen";
import DashboardScreen from "../screens/DashboardScreen";
import CasesScreen from "../screens/CasesScreen";
import CaseDetailScreen from "../screens/CaseDetailScreen";
import CaseFormScreen from "../screens/CaseFormScreen";
import CalendarScreen from "../screens/CalendarScreen";
import NotificationsScreen from "../screens/NotificationsScreen";
import DiscoveriesScreen from "../screens/DiscoveriesScreen";
import SettingsScreen from "../screens/SettingsScreen";
import EmailSetupScreen from "../screens/EmailSetupScreen";

const AuthStack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();
const CasesStack = createNativeStackNavigator();
const SettingsStack = createNativeStackNavigator();

function CasesStackNavigator() {
  return (
    <CasesStack.Navigator screenOptions={{ headerShown: false }}>
      <CasesStack.Screen name="CasesList" component={CasesScreen} />
      <CasesStack.Screen name="CaseDetail" component={CaseDetailScreen} />
      <CasesStack.Screen name="CaseForm" component={CaseFormScreen} />
    </CasesStack.Navigator>
  );
}

function SettingsStackNavigator() {
  return (
    <SettingsStack.Navigator screenOptions={{ headerShown: false }}>
      <SettingsStack.Screen name="SettingsMain" component={SettingsScreen} />
      <SettingsStack.Screen name="EmailSetup" component={EmailSetupScreen} />
      <SettingsStack.Screen name="Discoveries" component={DiscoveriesScreen} />
    </SettingsStack.Navigator>
  );
}

function MainTabs() {
  const [unreadCount, setUnreadCount] = useState(0);
  const [pendingDiscoveries, setPendingDiscoveries] = useState(0);
  const navigationRef = useRef<any>(null);

  // Fetch unread count periodically
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await notificationsApi.getUnreadCount();
      setUnreadCount(res.data.count);
    } catch {
      // Silently fail
    }
  }, []);

  const fetchPendingDiscoveries = useCallback(async () => {
    try {
      const res = await discoveryApi.getPendingCount();
      setPendingDiscoveries(res.data.count);
    } catch {
      // Silently fail
    }
  }, []);

  useEffect(() => {
    // Register for push notifications on mount
    registerForPushNotifications();

    // Fetch initial counts
    fetchUnreadCount();
    fetchPendingDiscoveries();

    // Poll every 60 seconds
    const interval = setInterval(() => {
      fetchUnreadCount();
      fetchPendingDiscoveries();
    }, 60000);

    // Handle notification taps - navigate to relevant case
    const cleanup = setupNotificationResponseListener((data) => {
      if (data.case_id && navigationRef.current) {
        navigationRef.current.navigate("CasesTab", {
          screen: "CaseDetail",
          params: { id: data.case_id },
        });
      } else if (navigationRef.current) {
        navigationRef.current.navigate("Notifications");
      }
    });

    return () => {
      clearInterval(interval);
      cleanup();
    };
  }, [fetchUnreadCount, fetchPendingDiscoveries]);

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: "#18181b",
        tabBarInactiveTintColor: "#9ca3af",
        tabBarStyle: {
          backgroundColor: "#fff",
          borderTopColor: "#e5e7eb",
          paddingBottom: 4,
          paddingTop: 4,
          height: 56,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "500" as const,
        },
        tabBarIcon: ({ focused, color }) => {
          let iconName: keyof typeof Ionicons.glyphMap = "help-outline";
          switch (route.name) {
            case "Dashboard":
              iconName = focused ? "grid" : "grid-outline";
              break;
            case "CasesTab":
              iconName = focused ? "folder" : "folder-outline";
              break;
            case "Calendar":
              iconName = focused ? "calendar" : "calendar-outline";
              break;
            case "Notifications":
              iconName = focused ? "notifications" : "notifications-outline";
              break;
            case "Settings":
              iconName = focused ? "settings" : "settings-outline";
              break;
          }
          return <Ionicons name={iconName} size={22} color={color} />;
        },
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen
        name="CasesTab"
        component={CasesStackNavigator}
        options={{ tabBarLabel: "Cases" }}
      />
      <Tab.Screen name="Calendar" component={CalendarScreen} />
      <Tab.Screen
        name="Notifications"
        component={NotificationsScreen}
        listeners={{
          tabPress: () => {
            // Refresh unread count when switching to notifications tab
            fetchUnreadCount();
          },
        }}
        options={{
          tabBarBadge: unreadCount > 0 ? unreadCount : undefined,
          tabBarBadgeStyle: badgeStyles.badge,
        }}
      />
      <Tab.Screen name="Settings" component={SettingsStackNavigator} />
    </Tab.Navigator>
  );
}

const badgeStyles = StyleSheet.create({
  badge: {
    backgroundColor: "#ef4444",
    fontSize: 10,
    fontWeight: "600",
    minWidth: 18,
    height: 18,
    borderRadius: 9,
  },
});

const discoverBadgeStyles = StyleSheet.create({
  badge: {
    backgroundColor: "#f59e0b",
    fontSize: 10,
    fontWeight: "600",
    minWidth: 18,
    height: 18,
    borderRadius: 9,
  },
});

export default function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#f9fafb" }}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      {user ? (
        <MainTabs />
      ) : (
        <AuthStack.Navigator screenOptions={{ headerShown: false }}>
          <AuthStack.Screen name="Login" component={LoginScreen} />
          <AuthStack.Screen name="Register" component={RegisterScreen} />
          <AuthStack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
          <AuthStack.Screen name="ResetPassword" component={ResetPasswordScreen} />
        </AuthStack.Navigator>
      )}
    </NavigationContainer>
  );
}
