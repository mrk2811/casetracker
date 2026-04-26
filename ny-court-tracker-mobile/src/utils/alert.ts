import { Alert, Platform } from "react-native";

/**
 * Cross-platform alert that works on both native and web.
 * React Native's Alert.alert() is a no-op on web, so we fall back to window.alert().
 */
export function showAlert(title: string, message: string): void {
  if (Platform.OS === "web") {
    window.alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
}
