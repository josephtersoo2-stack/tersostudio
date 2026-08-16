import { clearStoredToken, getStoredToken } from "./authToken";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | null | undefined>;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { params, headers = {}, ...restOptions } = options;

  let url = endpoint.startsWith("http")
    ? endpoint
    : `${API_BASE_URL.replace(/\/$/, "")}/${endpoint.replace(/^\//, "")}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const reqHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(headers as Record<string, string>),
  };

  const token = getStoredToken();
  if (token && !reqHeaders.Authorization) {
    reqHeaders.Authorization = `Token ${token}`;
  }

  const response = await fetch(url, {
    ...restOptions,
    headers: reqHeaders,
  });

  if (response.status === 401) {
    clearStoredToken();
    window.dispatchEvent(new CustomEvent("tersuite:auth:unauthorized"));
    throw new ApiError("Session expired or unauthorized. Please log in.", 401);
  }

  if (response.status === 403) {
    window.dispatchEvent(new CustomEvent("tersuite:auth:forbidden"));
    let errorData = null;
    try {
      errorData = await response.json();
    } catch {
      // Ignored
    }
    const message =
      errorData?.detail ||
      errorData?.message ||
      "Staff privileges are required to access this resource.";
    throw new ApiError(message, 403, errorData);
  }

  if (!response.ok) {
    let errorData = null;
    try {
      errorData = await response.json();
    } catch {
      // Non-JSON response
    }
    const message =
      errorData?.detail ||
      errorData?.message ||
      errorData?.error ||
      `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}
