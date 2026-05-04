const ADMIN_API_KEY_STORAGE = "admin_api_key";

export const getAdminApiKey = (): string | null => {
  const raw = localStorage.getItem(ADMIN_API_KEY_STORAGE);
  const trimmed = raw?.trim();
  return trimmed ? trimmed : null;
};

export const setAdminApiKey = (value: string): void => {
  localStorage.setItem(ADMIN_API_KEY_STORAGE, value.trim());
};

export const clearAdminApiKey = (): void => {
  localStorage.removeItem(ADMIN_API_KEY_STORAGE);
};

export const withAdminApiKeyHeader = (
  apiKey?: string,
): { "x-api-key": string } => {
  const resolved = apiKey?.trim() || getAdminApiKey();
  if (!resolved) {
    throw new Error("Admin API key is required.");
  }
  return { "x-api-key": resolved };
};
