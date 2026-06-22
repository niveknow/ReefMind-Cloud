import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('reefmind_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('reefmind_token');
      localStorage.removeItem('reefmind_tenant_id');
      localStorage.removeItem('reefmind_user_id');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default api;
