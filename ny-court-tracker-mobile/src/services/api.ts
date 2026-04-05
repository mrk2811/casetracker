import axios from "axios";
import { storage } from "./storage";

const API_URL = "https://app-ujjdvsxl.fly.dev";

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use(async (config) => {
  const token = await storage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  attorney_reg_number: string | null;
  created_at: string;
}

export interface FreshnessInfo {
  last_checked_at: string | null;
  last_source: string | null;
  hours_since_check: number | null;
  status: "fresh" | "stale" | "outdated" | "unknown";
}

export interface Case {
  id: number;
  user_id: number;
  court_type: string;
  county: string;
  index_number: string;
  case_year: number | null;
  case_status: string;
  plaintiff: string | null;
  defendant: string | null;
  plaintiff_firm: string | null;
  defendant_firm: string | null;
  justice: string | null;
  part: string | null;
  notes: string | null;
  priority: string;
  source: string;
  last_checked_at: string | null;
  last_source: string | null;
  verified: boolean;
  court_system: string | null;
  created_at: string;
  updated_at: string;
  next_appearance: string | null;
  freshness: FreshnessInfo | null;
}

export interface Appearance {
  id: number;
  case_id: number;
  appearance_date: string;
  appearance_time: string | null;
  appearance_type: string | null;
  location: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardAppearance {
  appearance_id: number;
  case_id: number;
  appearance_date: string;
  appearance_time: string | null;
  appearance_type: string | null;
  location: string | null;
  court_type: string;
  county: string;
  index_number: string;
  case_status: string;
  plaintiff: string | null;
  defendant: string | null;
  justice: string | null;
  part: string | null;
  priority: string;
  source: string;
  freshness: FreshnessInfo | null;
}

export interface CaseSearchResult {
  index_number: string;
  court_type: string;
  county: string;
  case_year: number | null;
  case_status: string | null;
  plaintiff: string | null;
  defendant: string | null;
  plaintiff_firm: string | null;
  defendant_firm: string | null;
  justice: string | null;
  part: string | null;
  last_action: string | null;
  last_action_date: string | null;
  source: string;
}

export interface CaseSearchResponse {
  results: CaseSearchResult[];
  court_system: string;
  message: string;
}

export interface CourtConfig {
  id: number;
  state: string;
  court_system: string;
  display_name: string;
  base_url: string | null;
  adapter_class: string;
  enabled: boolean;
}

export interface CaseEvent {
  id: number;
  case_id: number;
  event_type: string;
  event_date: string | null;
  description: string | null;
  source: string;
  created_at: string;
}

export interface NotificationSettings {
  id: number;
  user_id: number;
  email_enabled: boolean;
  push_enabled: boolean;
  reminder_days: number;
  case_updates_enabled: boolean;
  digest_frequency: string;
  digest_time: string;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  case_id: number | null;
  appearance_id: number | null;
  type: string;
  title: string;
  message: string;
  read: boolean;
  push_sent: boolean;
  created_at: string;
}

export interface PushTokenData {
  token: string;
  device_name?: string;
  platform?: string;
}

export interface CaseNotificationPrefs {
  case_id: number;
  user_id: number;
  push_enabled: boolean;
  email_enabled: boolean;
  priority_override: string | null;
}

// Auth
export const authApi = {
  register: (data: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    attorney_reg_number?: string;
  }) => api.post("/api/auth/register", data),
  login: (data: { email: string; password: string }) =>
    api.post("/api/auth/login", data),
  me: () => api.get<User>("/api/auth/me"),
};

// Cases
export const casesApi = {
  list: (params?: {
    court_type?: string;
    county?: string;
    status?: string;
    priority?: string;
    source?: string;
    verified?: boolean;
    sort_by?: string;
  }) => api.get<Case[]>("/api/cases", { params }),
  get: (id: number) => api.get<Case>(`/api/cases/${id}`),
  create: (data: Partial<Case>) => api.post<Case>("/api/cases", data),
  update: (id: number, data: Partial<Case>) =>
    api.put<Case>(`/api/cases/${id}`, data),
  delete: (id: number) => api.delete(`/api/cases/${id}`),
  search: (data: {
    index_number: string;
    court_type: string;
    county: string;
    court_system?: string;
  }) => api.post<CaseSearchResponse>("/api/cases/search", data),
  verify: (data: Partial<Case> & { court_system?: string; search_params?: string }) =>
    api.post<Case>("/api/cases/verify", data),
  getEvents: (caseId: number) =>
    api.get<CaseEvent[]>(`/api/cases/${caseId}/events`),
  getFreshness: (caseId: number) =>
    api.get<FreshnessInfo>(`/api/cases/${caseId}/freshness`),
  updatePriority: (caseId: number, priority: string) =>
    api.put<Case>(`/api/cases/${caseId}/priority`, null, { params: { priority } }),
};

// Appearances
export const appearancesApi = {
  list: (caseId: number) =>
    api.get<Appearance[]>(`/api/cases/${caseId}/appearances`),
  create: (caseId: number, data: Partial<Appearance>) =>
    api.post<Appearance>(`/api/cases/${caseId}/appearances`, data),
  update: (id: number, data: Partial<Appearance>) =>
    api.put<Appearance>(`/api/appearances/${id}`, data),
  delete: (id: number) => api.delete(`/api/appearances/${id}`),
};

// Dashboard
export const dashboardApi = {
  get: (params?: {
    court_type?: string;
    county?: string;
    priority?: string;
    source?: string;
    days_ahead?: number;
  }) => api.get<DashboardAppearance[]>("/api/dashboard", { params }),
  calendar: (params?: { month?: number; year?: number }) =>
    api.get<DashboardAppearance[]>("/api/dashboard/calendar", { params }),
};

// Court Configs
export const courtConfigsApi = {
  list: () => api.get<CourtConfig[]>("/api/court-configs"),
  adapters: () => api.get("/api/court-configs/adapters"),
};

// Scraper
export interface ScrapeJobResponse {
  id: number;
  case_id: number;
  court_system: string;
  status: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  result: string | null;
  error_message: string | null;
  created_at: string | null;
}

export interface ScraperStatusResponse {
  scheduler_running: boolean;
  jobs: { id: string; name: string; next_run: string | null }[];
  total_scrape_jobs: number;
  recent_failures: number;
}

export interface ManualScrapeResponse {
  status: string;
  case_id: number;
  last_action: string | null;
  error_message: string | null;
}

export const scraperApi = {
  getStatus: () => api.get<ScraperStatusResponse>("/api/scraper/status"),
  triggerManual: (caseId: number) =>
    api.post<ManualScrapeResponse>("/api/scraper/trigger-manual", { case_id: caseId }),
  getHistory: (caseId: number, limit?: number) =>
    api.get<ScrapeJobResponse[]>(`/api/scraper/history/${caseId}`, { params: { limit: limit || 20 } }),
  triggerBatch: (priority: string) =>
    api.post("/api/scraper/trigger-batch", null, { params: { priority } }),
};

// Email Integration
export interface EmailSetupResponse {
  inbound_email: string;
  forwarding_verified: boolean;
  provider: string | null;
  already_setup: boolean;
}

export interface EmailConfigResponse {
  id: number;
  user_id: number;
  inbound_email: string;
  forwarding_verified: boolean;
  provider: string | null;
  created_at: string;
}

export interface EmailVerifyResponse {
  verified: boolean;
  inbound_email: string | null;
}

export interface EmailSetupGuideStep {
  step: number;
  title: string;
  description: string;
  url: string | null;
  completed: boolean;
}

export interface EmailSetupGuide {
  inbound_email: string | null;
  forwarding_verified: boolean;
  steps: EmailSetupGuideStep[];
  gmail_instructions: string;
  outlook_instructions: string;
  privacy_note: string;
}

export interface EmailLogEntry {
  id: number;
  sender: string | null;
  subject: string | null;
  events_extracted: number;
  received_at: string;
}

export const emailApi = {
  setup: () => api.post<EmailSetupResponse>("/api/email/setup"),
  getConfig: () => api.get<EmailConfigResponse>("/api/email/config"),
  verify: () => api.post<EmailVerifyResponse>("/api/email/verify"),
  deleteConfig: () => api.delete("/api/email/config"),
  getSetupGuide: () => api.get<EmailSetupGuide>("/api/email/setup-guide"),
  getLog: (limit?: number) =>
    api.get<EmailLogEntry[]>("/api/email/log", { params: { limit: limit || 20 } }),
  testWebhook: (data: { sender?: string; subject?: string; text: string }) =>
    api.post("/api/email/webhook/test", null, { params: data }),
};

// Discovery
export interface DiscoverySettings {
  id: number;
  user_id: number;
  enabled: boolean;
  attorney_name: string | null;
  attorney_reg_number: string | null;
  search_courts: string;
  search_county: string | null;
  last_run_at: string | null;
  next_run_at: string | null;
}

export interface DiscoveredCase {
  id: number;
  user_id: number;
  index_number: string;
  court_type: string;
  county: string | null;
  court_system: string | null;
  plaintiff: string | null;
  defendant: string | null;
  case_status: string | null;
  last_action: string | null;
  last_action_date: string | null;
  source_adapter: string | null;
  status: string;
  notification_id: number | null;
  discovered_at: string;
  resolved_at: string | null;
}

export interface DiscoveryAcceptResponse {
  status: string;
  case_id: number | null;
  message: string;
}

export interface DiscoveryRunResponse {
  users_checked: number;
  total_discoveries: number;
  errors: number;
}

export const discoveryApi = {
  getSettings: () =>
    api.get<DiscoverySettings>("/api/discovery/settings"),
  updateSettings: (data: Partial<DiscoverySettings>) =>
    api.put<DiscoverySettings>("/api/discovery/settings", data),
  list: (params?: { status?: string; limit?: number }) =>
    api.get<DiscoveredCase[]>("/api/discovery", { params }),
  getPendingCount: () =>
    api.get<{ count: number }>("/api/discovery/pending-count"),
  accept: (discoveryId: number) =>
    api.post<DiscoveryAcceptResponse>(`/api/discovery/${discoveryId}/accept`),
  dismiss: (discoveryId: number) =>
    api.post<{ status: string; message: string }>(`/api/discovery/${discoveryId}/dismiss`),
  trigger: () =>
    api.post<DiscoveryRunResponse>("/api/discovery/trigger"),
};

// Notifications
export const notificationsApi = {
  getSettings: () =>
    api.get<NotificationSettings>("/api/notifications/settings"),
  updateSettings: (data: Partial<NotificationSettings>) =>
    api.put<NotificationSettings>("/api/notifications/settings", data),
  list: (params?: { notification_type?: string; unread_only?: boolean; limit?: number }) =>
    api.get<NotificationItem[]>("/api/notifications", { params }),
  markRead: (id: number) => api.put(`/api/notifications/${id}/read`),
  markAllRead: () => api.put("/api/notifications/read-all"),
  deleteNotification: (id: number) => api.delete(`/api/notifications/${id}`),
  clearAll: () => api.delete("/api/notifications"),
  getUnreadCount: () =>
    api.get<{ count: number }>("/api/notifications/unread-count"),
  // Push tokens
  registerPushToken: (data: PushTokenData) =>
    api.post("/api/notifications/push-token", data),
  unregisterPushToken: (token: string) =>
    api.delete("/api/notifications/push-token", { params: { token } }),
  // Per-case notification preferences
  getCasePrefs: (caseId: number) =>
    api.get<CaseNotificationPrefs>(`/api/notifications/case/${caseId}/prefs`),
  updateCasePrefs: (caseId: number, data: Partial<CaseNotificationPrefs>) =>
    api.put<CaseNotificationPrefs>(`/api/notifications/case/${caseId}/prefs`, data),
  // Trigger checks (testing)
  triggerChecks: () => api.post("/api/notifications/trigger-checks"),
};

export const setApiUrl = (url: string) => {
  api.defaults.baseURL = url;
};

export default api;
