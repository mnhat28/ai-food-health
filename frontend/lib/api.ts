import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(error);
  }
);

// ==========================================
// Auth
// ==========================================

export const authApi = {
  register: async (data: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
  }) => {
    const res = await api.post("/api/auth/register", data);
    return res.data;
  },

  login: async (data: { email: string; password: string }) => {
    const res = await api.post("/api/auth/login", data);
    return res.data;
  },

  getMe: async () => {
    const res = await api.get("/api/auth/me");
    return res.data;
  },

  updateProfile: async (data: Record<string, unknown>) => {
    const res = await api.put("/api/auth/me", data);
    return res.data;
  },

  deleteAccount: async () => {
    await api.delete("/api/auth/me");
  },
};

// ==========================================
// Food
// ==========================================

export const foodApi = {
  analyzeImage: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post("/api/food/analyze", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },

  search: async (query: string, limit = 10) => {
    const res = await api.get("/api/food/search", {
      params: { query, limit },
    });
    return res.data;
  },

  getFoodItem: async (foodId: string) => {
    const res = await api.get(`/api/food/items/${foodId}`);
    return res.data;
  },
};

// ==========================================
// Logs
// ==========================================

export const logsApi = {
  createLog: async (data: Record<string, unknown>) => {
    const res = await api.post("/api/logs/", data);
    return res.data;
  },

  getLogs: async (params?: {
    date?: string;
    meal_type?: string;
    limit?: number;
    offset?: number;
  }) => {
    const res = await api.get("/api/logs/", { params });
    return res.data;
  },

  getDailySummary: async (date: string) => {
    const res = await api.get("/api/logs/daily-summary", {
      params: { date },
    });
    return res.data;
  },

  getWeeklySummary: async (weekStart: string) => {
    const res = await api.get("/api/logs/weekly-summary", {
      params: { week_start: weekStart },
    });
    return res.data;
  },

  updateLog: async (logId: string, data: Record<string, unknown>) => {
    const res = await api.put(`/api/logs/${logId}`, data);
    return res.data;
  },

  deleteLog: async (logId: string) => {
    await api.delete(`/api/logs/${logId}`);
  },
};

// ==========================================
// Advice
// ==========================================

export const adviceApi = {
  getAdvice: async (message: string, dateRange = 7) => {
    const res = await api.post("/api/advice/", {
      message,
      date_range: dateRange,
    });
    return res.data;
  },

  getDailyTip: async () => {
    const res = await api.get("/api/advice/daily-tip");
    return res.data;
  },

  getWeeklyReport: async () => {
    const res = await api.get("/api/advice/weekly-report");
    return res.data;
  },

  streamAdvice: (message: string, dateRange = 7): EventSource => {
    const token = localStorage.getItem("access_token");
    const url = new URL(`${API_URL}/api/advice/stream`);
    url.searchParams.set("message", message);
    url.searchParams.set("date_range", String(dateRange));
    url.searchParams.set("token", token || "");
    return new EventSource(url.toString());
  },
};

export default api;