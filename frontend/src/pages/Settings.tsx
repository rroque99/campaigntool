import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuthStatus, usePlaywrightLogin, useSendQuota, useSetSendBackend } from "../api/campaigns";
import apiClient from "../api/client";

export default function Settings() {
  const { data: auth, isLoading: loadingAuth, refetch: refetchAuth } = useAuthStatus();
  const { data: quota } = useSendQuota();
  const [searchParams, setSearchParams] = useSearchParams();
  const [toast, setToast] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const playwrightLogin = usePlaywrightLogin();
  const setSendBackend = useSetSendBackend();

  const isPlaywright = auth?.send_backend === "playwright";

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

  async function handlePlaywrightLogin() {
    try {
      await playwrightLogin.mutateAsync();
      setToast("Browser launched. Complete the Gmail login in the browser window.");
      const timer = setTimeout(() => setToast(null), 8000);
      return () => clearTimeout(timer);
    } catch {
      setToast(null);
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

      {/* Sender Mode */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900">Email Sender</h2>
        {loadingAuth ? (
          <p className="mt-2 text-sm text-gray-500">Loading sender configuration...</p>
        ) : (
          <div className="mt-3 space-y-2">
            <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 hover:bg-gray-50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50">
              <input
                type="radio"
                name="send_backend"
                value="gmail_api"
                checked={!isPlaywright}
                disabled={setSendBackend.isPending}
                onChange={() => setSendBackend.mutate("gmail_api")}
                className="h-4 w-4 text-blue-600"
              />
              <div>
                <span className="text-sm font-medium text-gray-900">Gmail API</span>
                <p className="text-xs text-gray-500">Send via Google API with OAuth. Supports reply monitoring.</p>
              </div>
            </label>
            <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 hover:bg-gray-50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50">
              <input
                type="radio"
                name="send_backend"
                value="playwright"
                checked={isPlaywright}
                disabled={setSendBackend.isPending}
                onChange={() => setSendBackend.mutate("playwright")}
                className="h-4 w-4 text-blue-600"
              />
              <div>
                <span className="text-sm font-medium text-gray-900">Playwright (Browser Automation)</span>
                <p className="text-xs text-gray-500">Automate Gmail web UI. No API credentials needed.</p>
              </div>
            </label>
            {setSendBackend.isPending && (
              <p className="text-sm text-gray-500">Switching backend...</p>
            )}
            {setSendBackend.isError && (
              <p className="text-sm text-red-600">{setSendBackend.error.message}</p>
            )}
          </div>
        )}
      </section>

      {/* Gmail API Connection — only shown in gmail_api mode */}
      {!isPlaywright && (
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
      )}

      {/* Playwright Session — only shown in playwright mode */}
      {isPlaywright && (
        <section className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900">Playwright Session</h2>
          {loadingAuth ? (
            <p className="mt-2 text-sm text-gray-500">Checking session...</p>
          ) : auth.playwright_session_active ? (
            <div className="mt-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
                <span className="text-sm text-gray-700">
                  Session active{auth.playwright_session_email ? ` (${auth.playwright_session_email})` : ""}
                </span>
              </div>
              <button
                onClick={handlePlaywrightLogin}
                disabled={playwrightLogin.isPending}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {playwrightLogin.isPending ? "Opening browser..." : "Re-login"}
              </button>
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-400" />
                <span className="text-sm text-gray-500">No active session</span>
              </div>
              <button
                onClick={handlePlaywrightLogin}
                disabled={playwrightLogin.isPending}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {playwrightLogin.isPending ? "Opening browser..." : "Open Gmail Login"}
              </button>
              {playwrightLogin.isError && (
                <p className="text-sm text-red-600">{playwrightLogin.error.message}</p>
              )}
            </div>
          )}
        </section>
      )}

      {/* Reply monitoring warning — only shown in playwright mode */}
      {isPlaywright && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-800">Reply monitoring unavailable</p>
          <p className="mt-1 text-sm text-amber-700">
            Reply monitoring is not available in Playwright mode. Recipients who reply will not have
            their remaining emails automatically cancelled.
          </p>
        </div>
      )}

      {/* Send Quota — only shown in gmail_api mode */}
      {!isPlaywright && (
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
      )}

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
