import { getKeycloak } from "./keycloak";

export type Patient = {
  id: string;
  external_id: string | null;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
};

export type Provider = {
  id: string;
  first_name: string;
  last_name: string;
  specialty: string;
  email: string | null;
  phone: string | null;
  bio: string | null;
};

export type Availability = {
  id: string;
  provider_id: string;
  available_date: string;
  start_time: string;
  end_time: string;
  is_available: boolean;
};

export type Appointment = {
  id: string;
  patient_id: string;
  provider_id: string;
  starts_at: string;
  ends_at: string;
  status: string;
  appointment_type: string;
  reason: string | null;
};

export type AgentResponse = { response: string };

export type PatientDocument = {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  category: string | null;
  description: string | null;
  created_at: string;
};

export type RecordSearchResponse = { documents: PatientDocument[] };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const keycloak = getKeycloak();
  await keycloak.updateToken(30);

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${keycloak.token ?? ""}`,
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail ?? `Request failed with status ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }

  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<Patient>("/api/me"),
  providers: (specialty?: string) =>
    request<Provider[]>(
      `/api/providers${specialty ? `?specialty=${encodeURIComponent(specialty)}` : ""}`,
    ),
  availability: (providerId: string, date: string) =>
    request<Availability[]>(
      `/api/providers/${providerId}/availability?requested_date=${encodeURIComponent(date)}`,
    ),
  appointments: () => request<Appointment[]>("/api/appointments"),
  book: (input: {
    provider_id: string;
    starts_at: string;
    ends_at: string;
    reason?: string;
  }) =>
    request<Appointment>("/api/appointments", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateStatus: (id: string, nextStatus: string) =>
    request<{ id: string; status: string }>(`/api/appointments/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: nextStatus }),
    }),
  chat: (message: string) =>
    request<AgentResponse>("/api/agent/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  recordAssistant: (message: string) =>
    request<AgentResponse>("/api/records/assistant", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  searchRecords: (query = "") =>
    request<RecordSearchResponse>(
      `/api/records/search${query ? `?q=${encodeURIComponent(query)}` : ""}`,
    ),
  documents: () => request<PatientDocument[]>("/api/documents"),
  uploadDocument: async (file: File, category?: string, description?: string) => {
    const keycloak = getKeycloak();
    await keycloak.updateToken(30);
    const form = new FormData();
    form.append("file", file);
    if (category?.trim()) form.append("category", category.trim());
    if (description?.trim()) form.append("description", description.trim());

    const response = await fetch(`${API_URL}/api/documents`, {
      method: "POST",
      headers: { Authorization: `Bearer ${keycloak.token ?? ""}` },
      body: form,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body?.detail ?? `Request failed with status ${response.status}`;
      throw new Error(typeof detail === "string" ? detail : "Upload failed");
    }
    return response.json() as Promise<PatientDocument>;
  },
};
