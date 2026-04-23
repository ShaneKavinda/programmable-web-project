import { apiClient } from "../lib/apiClient";
import { withAdminApiKeyHeader } from "../lib/adminApiKey";
import type { AuthResponse, User } from "../types";

export const issueTokenByUserId = async (userId: string): Promise<AuthResponse> => {
  const response = await apiClient.get(`/api/users/${userId}/token`);
  return response.data as AuthResponse;
};

export const getMyProfile = async (): Promise<User> => {
  const response = await apiClient.get("/api/users/me");
  return response.data.user as User;
};

export const updateMyProfile = async (payload: Partial<Pick<User, "firstname" | "lastname" | "email">>): Promise<User> => {
  const response = await apiClient.patch("/api/users/me", payload);
  return response.data.user as User;
};

export const getAllUsers = async (adminApiKey?: string): Promise<User[]> => {
  const response = await apiClient.get("/api/users/", {
    headers: withAdminApiKeyHeader(adminApiKey),
  });
  const data = response.data as { users?: User[]; items?: User[]; data?: User[] };
  return data.users ?? data.items ?? data.data ?? [];
};

