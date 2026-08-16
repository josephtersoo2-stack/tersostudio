/**
 * Manages operator authentication tokens in local storage.
 * Isolated behind this module so storage strategy can be upgraded if needed.
 */

const TOKEN_STORAGE_KEY = "tersuite_control_center_token";

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch (err) {
    console.error("Failed to persist auth token", err);
  }
}

export function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    console.error("Failed to clear auth token", err);
  }
}
