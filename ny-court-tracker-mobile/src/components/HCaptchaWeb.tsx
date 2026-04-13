/**
 * HCaptcha widget for Expo Web.
 *
 * Loads the hCaptcha JS SDK via a <script> tag and renders the checkbox
 * widget inside a container div.  When the user completes the challenge
 * the `onVerify` callback fires with the response token that can be sent
 * to the backend.
 *
 * This component only works on the **web** platform (Expo Web / React
 * Native Web).  On native iOS/Android a WebView-based approach would be
 * needed instead — but the deployed app currently runs as web only.
 */

import React, { useEffect, useRef, useCallback } from "react";
import { View, StyleSheet, Platform, Text } from "react-native";

// Extend window to include hcaptcha global
declare global {
  interface Window {
    hcaptcha?: {
      render: (
        container: string | HTMLElement,
        params: {
          sitekey: string;
          callback?: (token: string) => void;
          "expired-callback"?: () => void;
          "error-callback"?: (err: unknown) => void;
          size?: string;
        }
      ) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
  }
}

interface HCaptchaWebProps {
  sitekey: string;
  onVerify: (token: string) => void;
  onError?: (err: unknown) => void;
  onExpire?: () => void;
}

export default function HCaptchaWeb({
  sitekey,
  onVerify,
  onError,
  onExpire,
}: HCaptchaWebProps) {
  const containerRef = useRef<View>(null);
  const widgetIdRef = useRef<string | null>(null);
  const scriptLoadedRef = useRef(false);

  const renderWidget = useCallback(() => {
    if (Platform.OS !== "web") return;
    if (!window.hcaptcha) return;

    const container = document.getElementById("hcaptcha-container");
    if (!container) return;

    // Remove previous widget if any
    if (widgetIdRef.current !== null) {
      try {
        window.hcaptcha.remove(widgetIdRef.current);
      } catch {
        // ignore
      }
      widgetIdRef.current = null;
    }

    // Clear the container
    container.innerHTML = "";

    try {
      const id = window.hcaptcha.render(container, {
        sitekey,
        callback: onVerify,
        "expired-callback": onExpire,
        "error-callback": onError,
        size: "normal",
      });
      widgetIdRef.current = id;
    } catch (err) {
      console.error("hCaptcha render error:", err);
      if (onError) onError(err);
    }
  }, [sitekey, onVerify, onError, onExpire]);

  useEffect(() => {
    if (Platform.OS !== "web") return;

    // Check if script is already loaded
    if (window.hcaptcha) {
      renderWidget();
      return;
    }

    // Check if script tag already exists
    const existing = document.querySelector(
      'script[src*="js.hcaptcha.com"]'
    );
    if (existing && !scriptLoadedRef.current) {
      existing.addEventListener("load", () => {
        scriptLoadedRef.current = true;
        renderWidget();
      });
      return;
    }

    if (!existing) {
      const script = document.createElement("script");
      script.src = "https://js.hcaptcha.com/1/api.js?render=explicit";
      script.async = true;
      script.defer = true;
      script.onload = () => {
        scriptLoadedRef.current = true;
        renderWidget();
      };
      script.onerror = () => {
        console.error("Failed to load hCaptcha script");
        if (onError) onError(new Error("Failed to load hCaptcha script"));
      };
      document.head.appendChild(script);
    }

    return () => {
      if (widgetIdRef.current !== null && window.hcaptcha) {
        try {
          window.hcaptcha.remove(widgetIdRef.current);
        } catch {
          // ignore
        }
        widgetIdRef.current = null;
      }
    };
  }, [renderWidget, onError]);

  if (Platform.OS !== "web") {
    return (
      <View style={styles.container}>
        <Text style={styles.unsupportedText}>
          CAPTCHA verification is only supported on the web version.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container} ref={containerRef}>
      {/* The hCaptcha widget renders into this div */}
      <div
        id="hcaptcha-container"
        style={{ minHeight: 78, display: "flex", justifyContent: "center" }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 12,
  },
  unsupportedText: {
    fontSize: 13,
    color: "#6b7280",
    textAlign: "center",
  },
});
