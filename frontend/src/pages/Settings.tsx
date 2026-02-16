import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuthStatus, useSendQuota } from "../api/campaigns";
import apiClient from "../api/client";

export default function Settings() {
  const { data: auth, isLoading: loadingAuth, refetch: refetchAuth } = useAuthStatus();
  const { data: quota } = useSendQuota();
  const [searchParams, setSearchParams] = useSearchParams();
  const [toast, setToast] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);

  useEffect(() => {
    if (searchParams.get("auth") === "success") {
      setToast("Gmail connected successfully!");
      setSearchParams({}, { replace: true });
      refetchAuth();
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [searchParams, setSearchParams, refetchAuth]);

  async function handleConnect() {
    const { data } = await apiClient.get<{ auth_url: string }>("/auth/login");
    window.location.href = data.auth_url;
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    try {
      await apiClient.post("/auth/logout");
      await refetchAuth();
    } finally {
      setDisconnecting(false);
    }
  }

  const quotaPercent = quota ? Math.round((quota.sent_today / quota.limit) * 100) : 0;

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Toast */}
      {toast && (
        <div className="rounded-lg bg-green-50 p-4 text-sm text-green-700">
          {toast}
        </div>
      )}

      {/* Gmail Connection */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900">Gmail Connection</h2>
        {loadingAuth ? (
          <p className="mt-2 text-sm text-gray-500">Checking authentication...</p>
        ) : auth?.authenticated ? (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
              <span className="text-sm text-gray-700">Connected as {auth.email}</span>
            </div>
            <button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {disconnecting ? "Disconnecting..." : "Disconnect"}
            </button>
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-400" />
              <span className="text-sm text-gray-500">Not connected</span>
            </div>
            <button
              onClick={handleConnect}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Connect Gmail
            </button>
          </div>
        )}
      </section>

      {/* Send Quota */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900">Daily Send Quota</h2>
        {quota ? (
          <div className="mt-4 space-y-3">
            <div className="flex justify-between text-sm text-gray-600">
              <span>{quota.sent_today} sent</span>
              <span>{quota.limit} limit</span>
            </div>
            <div className="h-3 rounded-full bg-gray-200">
              <div
                className={`h-3 rounded-full transition-all ${quotaPercent > 80 ? "bg-red-500" : "bg-blue-600"}`}
                style={{ width: `${Math.min(quotaPercent, 100)}%` }}
              />
            </div>
            <p className="text-sm text-gray-500">{quota.remaining} remaining today</p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-gray-500">
            Connect Gmail to view send quota.
          </p>
        )}
      </section>

      {/* About */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900">About</h2>
        <p className="mt-2 text-sm text-gray-500">
          Gmail Email Campaign Tool v1.0.0
        </p>
      </section>
    </div>
  );
}
