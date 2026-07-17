import axios from 'axios';
import { queueMutation, processQueue } from './sync-queue';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach Token
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const rawToken = localStorage.getItem('access_token') || localStorage.getItem('token');
    if (rawToken) {
      config.headers.Authorization = `Bearer ${rawToken}`;
    }
  }
  return config;
});

// Response Interceptor: Offline Mutation Trapping
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    // If there is no response object, the server could not be reached
    if (!error.response && error.config && error.config.method !== 'get') {
      await queueMutation(error.config);
      
      // Reject with a mock payload so the UI catches it and displays the queue status gracefully
      return Promise.reject({
        response: {
          data: { detail: 'Network offline. Action securely queued for background sync.' }
        }
      });
    }
    return Promise.reject(error);
  }
);

// Bind Sync Processor to Network Restoration
if (typeof window !== 'undefined') {
  window.addEventListener('online', async () => {
    await processQueue(apiClient);
  });
}
