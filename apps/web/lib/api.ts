import { apiErrorMessage, networkErrorMessage } from "./api-errors";
import { getKeycloak } from "../app/keycloak";

export type Patient = {
  id: string;
  external_id: string | null;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
};
export type Provider = { id: string; first_name: string; last_name: string; specialty: string; email: string | null; phone: string | null; bio: string | null };
export type Availability = { id: string; provider_id: string; available_date: string; start_time: string; end_time: string; is_available: boolean };
export type Appointment = { id: string; patient_id: string; provider_id: string; starts_at: string; ends_at: string; status: string; appointment_type: string; reason: string | null };
export type AgentResponse = { response: string };
export type ResearchSource = { title: string; url: string };
export type ResearchResponse = { response: string; sources: ResearchSource[] };
export type ResearchMessage = { id: string; role: "user" | "assistant"; content: string; sources: ResearchSource[]; created_at: string };
export type ResearchSession = { id: string; title: string; created_at: string; updated_at: string; messages: ResearchMessage[] };
export type ResearchSessionSummary = Omit<ResearchSession, "messages">;
export type ConsultationResponse = { appointment_id: string; join_url: string };
export type PatientDocument = { id: string; original_filename: string; content_type: string; size_bytes: number; category: string | null; description: string | null; created_at: string };
export type RecordSearchResponse = { documents: PatientDocument[] };
export type ProviderRecordResponse = { document: PatientDocument; content: string | null };

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const keycloak = getKeycloak();
  try {
    await keycloak.updateToken(30);
  } catch {
    throw new Error("Your login session has expired. Please sign in again.");
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${keycloak.token ?? ""}`, ...(init.headers ?? {}) },
    });
  } catch (error) {
    throw new Error(networkErrorMessage(error));
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(apiErrorMessage(response.status, body?.detail));
  }
  try {
    return await response.json() as T;
  } catch {
    throw new Error("The service returned an invalid response. Please try again.");
  }
}

export const api = {
  me: () => request<Patient>("/api/me"),
  providerMe: () => request<Provider>("/api/me/provider"),
  providers: (specialty?: string) => request<Provider[]>(`/api/providers${specialty ? `?specialty=${encodeURIComponent(specialty)}` : ""}`),
  availability: (providerId: string, date: string) => request<Availability[]>(`/api/providers/${providerId}/availability?requested_date=${encodeURIComponent(date)}`),
  appointments: () => request<Appointment[]>("/api/appointments"),
  book: (input: { provider_id: string; starts_at: string; ends_at: string; reason?: string }) => request<Appointment>("/api/appointments", { method: "POST", body: JSON.stringify(input) }),
  updateStatus: (id: string, nextStatus: string) => request<{ id: string; status: string }>(`/api/appointments/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: nextStatus }) }),
  consultation: (id: string) => request<ConsultationResponse>(`/api/appointments/${id}/consultation`),
  createProviderAvailability: (input: { available_date: string; start_time: string; end_time: string }) => request<Availability>("/api/providers/me/availability", { method: "POST", body: JSON.stringify(input) }),
  providerRecords: (patientId: string) => request<PatientDocument[]>(`/api/provider/patients/${patientId}/records`),
  providerRecord: (patientId: string, documentId: string) => request<ProviderRecordResponse>(`/api/provider/patients/${patientId}/records/${documentId}`),
  chat: (message: string) => request<AgentResponse>("/api/agent/chat", { method: "POST", body: JSON.stringify({ message }) }),
  recordAssistant: (message: string) => request<AgentResponse>("/api/records/assistant", { method: "POST", body: JSON.stringify({ message }) }),
  research: (message: string) => request<ResearchResponse>("/api/research", { method: "POST", body: JSON.stringify({ message }) }),
  researchSessions: (query = "", offset = 0, limit = 20) => { const params = new URLSearchParams({ offset: String(offset), limit: String(limit) }); if (query.trim()) params.set("q", query.trim()); return request<ResearchSessionSummary[]>(`/api/research/sessions?${params.toString()}`); },
  createResearchSession: () => request<ResearchSession>("/api/research/sessions", { method: "POST" }),
  researchSession: (id: string) => request<ResearchSession>(`/api/research/sessions/${id}`),
  renameResearchSession: (id: string, title: string) => request<ResearchSession>(`/api/research/sessions/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ title }) }),
  deleteResearchSession: async (id: string): Promise<void> => {
    const keycloak = getKeycloak();
    await keycloak.updateToken(30);
    const response = await fetch(`${API_URL}/api/research/sessions/${encodeURIComponent(id)}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${keycloak.token ?? ""}` },
    });
    if (!response.ok) throw new Error("Unable to delete research session");
  },
  sendResearchMessage: (id: string, message: string) => request<ResearchSession>(`/api/research/sessions/${id}/messages`, { method: "POST", body: JSON.stringify({ message }) }),
  searchRecords: (query = "") => request<RecordSearchResponse>(`/api/records/search${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  documents: () => request<PatientDocument[]>("/api/documents"),
  uploadDocument: async (file: File, category?: string, description?: string) => {
    const keycloak = getKeycloak(); await keycloak.updateToken(30);
    const form = new FormData(); form.append("file", file); if (category?.trim()) form.append("category", category.trim()); if (description?.trim()) form.append("description", description.trim());
    const response = await fetch(`${API_URL}/api/documents`, { method: "POST", headers: { Authorization: `Bearer ${keycloak.token ?? ""}` }, body: form });
    if (!response.ok) { const body = await response.json().catch(() => null); const detail = body?.detail ?? `Request failed with status ${response.status}`; throw new Error(typeof detail === "string" ? detail : "Upload failed"); }
    return response.json() as Promise<PatientDocument>;
  },
  downloadDocument: async (id: string) => {
    const keycloak = getKeycloak(); await keycloak.updateToken(30); const response = await fetch(`${API_URL}/api/documents/${id}`, { headers: { Authorization: `Bearer ${keycloak.token ?? ""}` } });
    if (!response.ok) { const body = await response.json().catch(() => null); const detail = body?.detail ?? `Request failed with status ${response.status}`; throw new Error(typeof detail === "string" ? detail : "Download failed"); } return response.blob();
  },
  deleteDocument: async (id: string) => {
    const keycloak = getKeycloak(); await keycloak.updateToken(30); const response = await fetch(`${API_URL}/api/documents/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${keycloak.token ?? ""}` } });
    if (!response.ok) { const body = await response.json().catch(() => null); const detail = body?.detail ?? `Request failed with status ${response.status}`; throw new Error(typeof detail === "string" ? detail : "Delete failed"); }
  },
};
