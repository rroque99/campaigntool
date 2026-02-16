import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api/v1",
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response) {
      const detail = error.response.data?.detail ?? "An unexpected error occurred";
      return Promise.reject(new Error(detail));
    }
    return Promise.reject(error);
  },
);

export default apiClient;
