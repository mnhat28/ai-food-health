import { authApi } from "./api";

export const saveToken = (token: string) => {
  localStorage.setItem("access_token", token);
};

export const getToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
};

export const removeToken = () => {
  localStorage.removeItem("access_token");
};

export const isAuthenticated = (): boolean => {
  return !!getToken();
};

export const login = async (email: string, password: string) => {
  const data = await authApi.login({ email, password });
  saveToken(data.access_token);
  return data.user;
};

export const register = async (
  email: string,
  username: string,
  password: string,
  fullName?: string
) => {
  const data = await authApi.register({ email, username, password, full_name: fullName });
  saveToken(data.access_token);
  return data.user;
};

export const logout = () => {
  removeToken();
  window.location.href = "/auth/login";
};