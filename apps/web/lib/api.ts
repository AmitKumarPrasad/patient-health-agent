import { getKeycloak } from "../app/keycloak";

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
export type ConsultationResponse = { appointment_id: string; join_url: string };

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
export type ProviderRecordResponse = { document: PatientDocument; content: string | null };

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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