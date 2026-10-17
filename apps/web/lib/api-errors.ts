/** Safe, actionable API errors without echoing backend exception details. */
export function apiErrorMessage(status: number, detail?: unknown): string {
  if (status === 401) return "Your login session has expired. Please sign in again.";
  if (status === 403) return "Your account is not allowed to perform this action.";
  if (status === 429) return "Too many requests. Please wait and try again.";
  if (status === 502 || status === 503 || status === 504) {
    return "The service is temporarily unavailable. Please try again shortly.";
  }
  if (status >= 500) return "The service encountered an error. Please try again later.";
  if (typeof detail === "string" && detail.trim()) return detail;
  return `Request failed (HTTP ${status}). Please try again.`;
}

export function networkErrorMessage(error: unknown): string {
  if (error instanceof Error && error.name === "AbortError") {
    return "The request was cancelled. Please try again.";
  }
  return "Cannot connect to the application server. Check your connection and try again.";
}
