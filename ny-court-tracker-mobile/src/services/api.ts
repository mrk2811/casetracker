import axios from "axios";
import { storage } from "./storage";

const API_URL = "http://localhost:8000";

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
  created_at: string;
  updated_at: string;
  next_appearance: string | null;
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
}

export interface NotificationSettings {
  id: number;
  user_id: number;
  email_enabled: boolean;
  reminder_days: number;
  case_updates_enabled: boolean;
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
  created_at: string;
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
    sort_by?: string;
  }) => api.get<Case[]>("/api/cases", { params }),
  get: (id: number) => api.get<Case>(`/api/cases/${id}`),
  create: (data: Partial<Case>) => api.post<Case>("/api/cases", data),
  update: (id: number, data: Partial<Case>) =>
    api.put<Case>(`/api/cases/${id}`, data),
  delete: (id: number) => api.delete(`/api/cases/${id}`),
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
    days_ahead?: number;
  }) => api.get<DashboardAppearance[]>("/api/dashboard", { params }),
  calendar: (params?: { month?: number; year?: number }) =>
    api.get<DashboardAppearance[]>("/api/dashboard/calendar", { params }),
};

// Notifications
export const notificationsApi = {
  getSettings: () =>
    api.get<NotificationSettings>("/api/notifications/settings"),
  updateSettings: (data: Partial<NotificationSettings>) =>
    api.put<NotificationSettings>("/api/notifications/settings", data),
  list: () => api.get<NotificationItem[]>("/api/notifications"),
  markRead: (id: number) => api.put(`/api/notifications/${id}/read`),
  markAllRead: () => api.put("/api/notifications/read-all"),
};

export const setApiUrl = (url: string) => {
  api.defaults.baseURL = url;
};

export default api;
