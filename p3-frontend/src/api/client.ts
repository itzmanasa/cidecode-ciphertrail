import axios from "axios";

export const BASE_URL = "http://localhost:8001";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  // Kept short on purpose: when no backend is reachable (the common case for
  // this demo build), we want to fall back to mock data in a few seconds,
  // not make the UI sit on a loading skeleton for a full minute.
  timeout: 8000,
});

export class ApiError extends Error {
  isNetworkError: boolean;
  constructor(message: string, isNetworkError: boolean) {
    super(message);
    this.name = "ApiError";
    this.isNetworkError = isNetworkError;
  }
}

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    // No response at all (backend down, CORS failure, offline, timeout) means
    // this is a connectivity problem rather than a real API error — callers
    // use this flag to fall back to local mock data instead of showing an error.
    const isNetworkError = !error?.response;
    const message =
      error?.response?.data?.message ||
      error?.response?.data?.detail ||
      error?.message ||
      "Something went wrong while talking to the CipherTrail backend.";
    return Promise.reject(new ApiError(message, isNetworkError));
  }
);
