import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type {
  AuthStatus,
  Campaign,
  CampaignListResponse,
  CampaignStatusResponse,
  CancelResponse,
  EmailDetail,
  EmailListResponse,
  EmailPreview,
  PauseResponse,
  PlaywrightStatus,
  RecipientCreateRequest,
  RecipientCreateResponse,
  RecipientListResponse,
  ScheduleResponse,
  SendQuota,
} from "../types";

// --- Auth ---

export function useAuthStatus() {
  return useQuery<AuthStatus>({
    queryKey: ["auth", "status"],
    queryFn: async () => (await apiClient.get("/auth/status")).data,
  });
}

export function useSendQuota() {
  return useQuery<SendQuota>({
    queryKey: ["auth", "quota"],
    queryFn: async () => (await apiClient.get("/auth/quota")).data,
  });
}

export function usePlaywrightStatus() {
  return useQuery<PlaywrightStatus>({
    queryKey: ["auth", "playwright", "status"],
    queryFn: async () => (await apiClient.get("/auth/playwright/status")).data,
  });
}

export function useSetSendBackend() {
  const qc = useQueryClient();
  return useMutation<AuthStatus, Error, "gmail_api" | "playwright">({
    mutationFn: async (send_backend) =>
      (await apiClient.post("/auth/send-backend", { send_backend })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["auth"] });
    },
  });
}

export function usePlaywrightLogin() {
  const qc = useQueryClient();
  return useMutation<{ message: string }, Error, void>({
    mutationFn: async () => (await apiClient.post("/auth/playwright/login")).data,
    onSuccess: () => {
      // Poll auth status until the session becomes active (Gmail needs time to load)
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        await qc.invalidateQueries({ queryKey: ["auth"] });
        const data = qc.getQueryData<AuthStatus>(["auth", "status"]);
        if (data?.playwright_session_active || attempts >= 12) {
          clearInterval(poll);
        }
      }, 3000);
    },
  });
}

// --- Campaigns ---

export function useCampaigns(status?: string) {
  return useQuery<CampaignListResponse>({
    queryKey: ["campaigns", { status }],
    queryFn: async () => {
      const params = status ? { status } : {};
      return (await apiClient.get("/campaigns", { params })).data;
    },
  });
}

export function useCampaign(id: number | string) {
  return useQuery<Campaign>({
    queryKey: ["campaigns", id],
    queryFn: async () => (await apiClient.get(`/campaigns/${id}`)).data,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "scheduled" || s === "in_progress" ? 10_000 : false;
    },
  });
}

export function useCampaignStatus(id: number | string) {
  return useQuery<CampaignStatusResponse>({
    queryKey: ["campaigns", id, "status"],
    queryFn: async () => (await apiClient.get(`/campaigns/${id}/status`)).data,
    refetchInterval: (query) => {
      const d = query.state.data;
      if (!d) return false;
      return d.pending > 0 || d.scheduled > 0 ? 10_000 : false;
    },
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation<Campaign, Error, FormData>({
    mutationFn: async (formData) =>
      (await apiClient.post("/campaigns", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (id) => {
      await apiClient.delete(`/campaigns/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function useScheduleCampaign() {
  const qc = useQueryClient();
  return useMutation<ScheduleResponse, Error, number>({
    mutationFn: async (id) =>
      (await apiClient.post(`/campaigns/${id}/schedule`)).data,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["campaigns", id] });
      qc.invalidateQueries({ queryKey: ["campaigns", id, "status"] });
    },
  });
}

export function usePauseCampaign() {
  const qc = useQueryClient();
  return useMutation<PauseResponse, Error, number>({
    mutationFn: async (id) =>
      (await apiClient.post(`/campaigns/${id}/pause`)).data,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["campaigns", id] });
      qc.invalidateQueries({ queryKey: ["campaigns", id, "status"] });
    },
  });
}

export function useCancelCampaign() {
  const qc = useQueryClient();
  return useMutation<CancelResponse, Error, number>({
    mutationFn: async (id) =>
      (await apiClient.post(`/campaigns/${id}/cancel`)).data,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["campaigns", id] });
      qc.invalidateQueries({ queryKey: ["campaigns", id, "status"] });
    },
  });
}

// --- Recipients ---

export function useRecipients(
  campaignId: number | string,
  params?: { page?: number; page_size?: number; search?: string; status?: string },
) {
  return useQuery<RecipientListResponse>({
    queryKey: ["campaigns", campaignId, "recipients", params],
    queryFn: async () =>
      (await apiClient.get(`/campaigns/${campaignId}/recipients`, { params })).data,
    refetchInterval: (query) => {
      const d = query.state.data;
      if (!d) return false;
      const hasActive = d.items.some(
        (r) => r.email_status === "pending" || r.email_status === "scheduled",
      );
      return hasActive ? 10_000 : false;
    },
  });
}

export function useAddRecipient(campaignId: number) {
  const qc = useQueryClient();
  return useMutation<RecipientCreateResponse, Error, RecipientCreateRequest>({
    mutationFn: async (data) =>
      (await apiClient.post(`/campaigns/${campaignId}/recipients`, data)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns", campaignId, "recipients"] });
      qc.invalidateQueries({ queryKey: ["campaigns", campaignId] });
    },
  });
}

// --- Email Preview ---

export function useEmailPreview(campaignId: number | string, recipientId?: number) {
  return useQuery<EmailPreview[]>({
    queryKey: ["campaigns", campaignId, "preview", recipientId],
    queryFn: async () => {
      const params = recipientId ? { recipient_id: recipientId } : {};
      return (await apiClient.get(`/campaigns/${campaignId}/preview`, { params })).data;
    },
  });
}

// --- Emails ---

export function useEmails(
  campaignId: number | string,
  params?: { page?: number; page_size?: number; status?: string; sort_by?: string },
) {
  return useQuery<EmailListResponse>({
    queryKey: ["campaigns", campaignId, "emails", params],
    queryFn: async () =>
      (await apiClient.get(`/campaigns/${campaignId}/emails`, { params })).data,
    refetchInterval: (query) => {
      const d = query.state.data;
      if (!d) return false;
      const hasActive = d.items.some(
        (e) => e.status === "pending" || e.status === "scheduled",
      );
      return hasActive ? 10_000 : false;
    },
  });
}

export function useEmailDetail(campaignId: number | string, emailId: number | string) {
  return useQuery<EmailDetail>({
    queryKey: ["campaigns", campaignId, "emails", emailId],
    queryFn: async () =>
      (await apiClient.get(`/campaigns/${campaignId}/emails/${emailId}`)).data,
  });
}
