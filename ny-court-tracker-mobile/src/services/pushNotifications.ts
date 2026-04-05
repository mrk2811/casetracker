/**
 * Push Notification Service
 *
 * Handles Expo push notification registration, token management,
 * and notification event handling.
 */

import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import { Platform } from "react-native";
import { notificationsApi } from "./api";

// Configure how notifications appear when app is in foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

/**
 * Register for push notifications and send token to backend.
 * Returns the Expo push token string or null if registration fails.
 */
export async function registerForPushNotifications(): Promise<string | null> {
  // Push notifications only work on physical devices
  if (!Device.isDevice) {
    console.log("Push notifications require a physical device");
    return null;
  }

  try {
    // Check existing permissions
    const { status: existingStatus } =
      await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    // Request permissions if not granted
    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== "granted") {
      console.log("Push notification permission not granted");
      return null;
    }

    // Get the Expo push token
    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId;

    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId: projectId || undefined,
    });

    const token = tokenData.data;
    console.log("Expo push token:", token);

    // Register token with backend
    try {
      await notificationsApi.registerPushToken({
        token,
        device_name: Device.modelName || undefined,
        platform: Platform.OS,
      });
      console.log("Push token registered with backend");
    } catch (err) {
      console.error("Failed to register push token with backend:", err);
    }

    // Set up Android notification channel
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "Default",
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: "#3b82f6",
      });

      await Notifications.setNotificationChannelAsync("court-reminders", {
        name: "Court Reminders",
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: "#ef4444",
      });

      await Notifications.setNotificationChannelAsync("case-updates", {
        name: "Case Updates",
        importance: Notifications.AndroidImportance.DEFAULT,
      });
    }

    return token;
  } catch (error) {
    console.error("Error registering for push notifications:", error);
    return null;
  }
}

/**
 * Unregister push token from backend.
 */
export async function unregisterPushToken(token: string): Promise<void> {
  try {
    await notificationsApi.unregisterPushToken(token);
    console.log("Push token unregistered");
  } catch (err) {
    console.error("Failed to unregister push token:", err);
  }
}

/**
 * Set up notification response listener (when user taps a notification).
 * Returns a cleanup function.
 */
export function setupNotificationResponseListener(
  onNotificationTap: (data: Record<string, unknown>) => void
): () => void {
  const subscription = Notifications.addNotificationResponseReceivedListener(
    (response) => {
      const data = response.notification.request.content.data || {};
      onNotificationTap(data as Record<string, unknown>);
    }
  );
  return () => subscription.remove();
}

/**
 * Set up listener for notifications received while app is in foreground.
 * Returns a cleanup function.
 */
export function setupNotificationReceivedListener(
  onNotification: (notification: Notifications.Notification) => void
): () => void {
  const subscription =
    Notifications.addNotificationReceivedListener(onNotification);
  return () => subscription.remove();
}

/**
 * Get the current badge count.
 */
export async function getBadgeCount(): Promise<number> {
  return await Notifications.getBadgeCountAsync();
}

/**
 * Set the badge count on the app icon.
 */
export async function setBadgeCount(count: number): Promise<void> {
  await Notifications.setBadgeCountAsync(count);
}
