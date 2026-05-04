import { apiClient } from "../lib/apiClient";
import { withAdminApiKeyHeader } from "../lib/adminApiKey";
import type { Flight, PaginatedResponse } from "../types";

export type FlightSearchFilters = {
  status?: "all" | "active" | "inactive" | "started" | "en_route" | "landed" | "cancelled" | "delayed";
  origin_airport?: string;
  destination_airport?: string;
  departure_date?: string;
  arrival_date?: string;
  page?: number;
  per_page?: number;
  sort_by?: "departure_time" | "arrival_time" | "base_price";
  sort_order?: "asc" | "desc";
};

function sanitizeFlightSearchFilters(filters: FlightSearchFilters): Record<string, string | number> {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== "" && value != null),
  ) as Record<string, string | number>;
}

export const searchFlights = async (filters: FlightSearchFilters): Promise<Flight[]> => {
  const response = await apiClient.get("/api/flights/search", {
    params: sanitizeFlightSearchFilters(filters),
  });
  const data = response.data as PaginatedResponse<Flight>;
  return data.flights ?? data.items ?? data.data ?? [];
};

export const searchFlightsPaginated = async (
  filters: FlightSearchFilters,
): Promise<{ flights: Flight[]; pagination: NonNullable<PaginatedResponse<Flight>["pagination"]> }> => {
  const response = await apiClient.get("/api/flights/search", {
    params: sanitizeFlightSearchFilters(filters),
  });
  const data = response.data as PaginatedResponse<Flight>;
  return {
    flights: data.flights ?? data.items ?? data.data ?? [],
    pagination: data.pagination ?? {
      page: filters.page ?? 1,
      per_page: filters.per_page ?? 10,
      total_pages: 1,
      total_items: 0,
      has_next: false,
      has_prev: false,
      next_page: null,
      prev_page: null,
    },
  };
};

export const searchAllFlights = async (filters: FlightSearchFilters): Promise<Flight[]> => {
  const perPage = 100;
  let page = 1;
  const allFlights: Flight[] = [];

  while (true) {
    const { flights, pagination } = await searchFlightsPaginated({
      ...filters,
      page,
      per_page: perPage,
    });
    allFlights.push(...flights);
    if (!pagination.has_next) break;
    page += 1;
  }

  return allFlights;
};

export const listAirports = async (): Promise<string[]> => {
  const response = await apiClient.get("/api/flights/airports");
  const data = response.data as { airports?: string[] };
  return data.airports ?? [];
};

type AdminFlightPayload = {
  flight_code: string;
  origin_airport: string;
  destination_airport: string;
  departure_time: string;
  arrival_time: string;
  base_price: number;
  status?: "active" | "inactive" | "started" | "en_route" | "landed" | "cancelled" | "delayed";
};

export const createFlight = async (
  payload: AdminFlightPayload,
  adminApiKey?: string,
): Promise<Flight> => {
  const response = await apiClient.post("/api/flights/", payload, {
    headers: withAdminApiKeyHeader(adminApiKey),
  });
  return (response.data as { flight?: Flight }).flight as Flight;
};

export const updateFlight = async (
  flightId: string,
  payload: Partial<AdminFlightPayload>,
  adminApiKey?: string,
): Promise<Flight> => {
  const response = await apiClient.put(`/api/flights/${flightId}`, payload, {
    headers: withAdminApiKeyHeader(adminApiKey),
  });
  return (response.data as { flight?: Flight }).flight as Flight;
};

export const deleteFlight = async (
  flightId: string,
  adminApiKey?: string,
): Promise<void> => {
  await apiClient.delete(`/api/flights/${flightId}`, {
    headers: withAdminApiKeyHeader(adminApiKey),
  });
};

export async function getFlightById(flightId: string): Promise<Flight | null> {
  try {
    const response = await apiClient.get(`/api/flights/${flightId}`);
    const data = response.data as { flight?: Flight };
    return data.flight ?? null;
  } catch {
    return null;
  }
}

export async function getFlightsByIds(flightIds: string[]): Promise<Map<string, Flight>> {
  const unique = [...new Set(flightIds.filter(Boolean))];
  const map = new Map<string, Flight>();
  const results = await Promise.allSettled(unique.map((id) => getFlightById(id)));
  for (let i = 0; i < unique.length; i++) {
    const result = results[i];
    if (result.status === "fulfilled" && result.value) {
      map.set(unique[i], result.value);
    }
  }
  return map;
}

