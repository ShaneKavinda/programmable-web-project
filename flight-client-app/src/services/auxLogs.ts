import { apiClient } from "../lib/apiClient";
import { withAdminApiKeyHeader } from "../lib/adminApiKey";

export type AuxNotificationLog = {
  id: string;
  event_type: string;
  booking_id: string;
  user_id: string;
  user_email: string;
  source: string;
  status: string;
  delivery_channel: string;
  delivery_message: string;
  payload: Record<string, unknown>;
  occurred_at: string;
  received_at: string;
};

export const getAuxLogs = async (params?: {
  booking_id?: string;
  limit?: number;
}, adminApiKey?: string): Promise<{ notifications: AuxNotificationLog[]; count: number }> => {
  const response = await apiClient.get("/api/aux/notifications", {
    params,
    headers: withAdminApiKeyHeader(adminApiKey),
  });
  return response.data as { notifications: AuxNotificationLog[]; count: number };
};
