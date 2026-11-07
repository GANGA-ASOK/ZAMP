/**
 * Centralized Axios API client for VendorFlow.
 *
 * Base URL is read from VITE_API_BASE_URL in .env.
 * All API calls go through this instance so error handling,
 * headers, and timeouts are configured in one place.
 */

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

if (!BASE_URL) {
  console.warn(
    '[VendorFlow] VITE_API_BASE_URL is not set. ' +
    'Create a .env file with VITE_API_BASE_URL=http://localhost:8000/api'
  );
}

const apiClient = axios.create({
  baseURL: BASE_URL ?? 'http://localhost:8000/api',
  timeout: 30_000,
  headers: {
    'Accept': 'application/json',
  },
});

// Global response interceptor — normalise error shape
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      const detail = error.response?.data?.detail;
      if (typeof detail === 'string') {
        error.message = detail;
      } else if (detail?.message) {
        error.message = detail.message;
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

