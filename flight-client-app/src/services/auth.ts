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

type UsersPageResponse = {
  users: User[];
  pagination: {
    page: number;
    per_page: number;
    total_pages: number;
    total_items: number;
    has_next: boolean;
    has_prev: boolean;
    next_page: number | null;
    prev_page: number | null;
  };
};

export const getUsersPage = async (
  params: { page: number; per_page: number },
  adminApiKey?: string,
): Promise<UsersPageResponse> => {
  const response = await apiClient.get("/api/users/", {
    params,
    headers: withAdminApiKeyHeader(adminApiKey),
  });
  const data = response.data as {
    users?: Array<User | { user?: User }>;
    pagination?: UsersPageResponse["pagination"];
  };
  const rawUsers = data.users ?? [];
  const normalizedUsers = rawUsers
    .map((row) => ("user" in (row as { user?: User }) ? (row as { user?: User }).user : (row as User)))
    .filter((u): u is User => Boolean(u?.id));

  return {
    users: normalizedUsers,
    pagination: data.pagination ?? {
      page: params.page,
      per_page: params.per_page,
      total_pages: 0,
      total_items: 0,
      has_next: false,
      has_prev: false,
      next_page: null,
      prev_page: null,
    },
  };
};

