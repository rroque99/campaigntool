import { Link } from "react-router-dom";
import { useAuthStatus, useCampaigns, useSendQuota } from "../api/campaigns";
import StatusBadge from "../components/StatusBadge";
import type { CampaignStatus } from "../types";

export default function Dashboard() {
  const { data: campaignsData, isLoading: loadingCampaigns } = useCampaigns();
  const { data: quota } = useSendQuota();
  const { data: auth } = useAuthStatus();

  const campaigns = campaignsData?.campaigns ?? [];
  const activeCampaigns = campaigns.filter(
    (c) => c.status === "scheduled" || c.status === "in_progress",
  );
  const totalSent = campaigns.reduce((sum, c) => sum + c.sent_count, 0);

  const stats = [
    { label: "Total Campaigns", value: campaigns.length },
    { label: "Active", value: activeCampaigns.length },
    { label: "Sent Today", value: quota?.sent_today ?? 0 },
    { label: "Quota Remaining", value: quota?.remaining ?? "-" },
  ];

  if (loadingCampaigns) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          {auth && (
            <span className="inline-block rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
              {auth.send_backend === "playwright" ? "Playwright" : "Gmail API"}
            </span>
          )}
        </div>
        {auth && !auth.authenticated && auth.send_backend === "gmail_api" && (
          <Link
            to="/settings"
            className="rounded-lg bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700 hover:bg-amber-100"
          >
            Connect Gmail to get started
          </Link>
        )}
      </div>

      {/* Playwright session not active warning */}
      {auth?.send_backend === "playwright" && !auth.playwright_session_active && (
        <Link
          to="/settings"
          className="block rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700 hover:bg-amber-100"
        >
          Playwright session not active — campaigns cannot send emails. Click here to open Settings.
        </Link>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-xl border border-gray-200 bg-white p-5">
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{stat.value}</p>
          </div>
        ))}
      </div>

      {campaigns.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white py-16 text-center">
          <p className="text-gray-500">No campaigns yet.</p>
          <Link
            to="/campaigns/new"
            className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Create your first campaign
          </Link>
        </div>
      ) : (
        <>
          {/* Recent campaigns */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Recent Campaigns</h2>
              <Link to="/campaigns" className="text-sm text-blue-600 hover:text-blue-700">
                View all
              </Link>
            </div>
            <div className="space-y-3">
              {campaigns.slice(0, 5).map((c) => (
                <Link
                  key={c.id}
                  to={`/campaigns/${c.id}`}
                  className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 transition-colors hover:bg-gray-50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-gray-900">{c.name}</p>
                    <p className="text-sm text-gray-500">
                      {c.recipient_count} recipients &middot; {c.sent_count}/{c.recipient_count * c.step_count} sent
                    </p>
                  </div>
                  <div className="ml-4 flex items-center gap-3">
                    {/* Progress bar */}
                    {c.recipient_count > 0 && c.step_count > 0 && (
                      <div className="hidden w-32 sm:block">
                        <div className="h-2 rounded-full bg-gray-200">
                          <div
                            className="h-2 rounded-full bg-blue-600 transition-all"
                            style={{
                              width: `${Math.round((c.sent_count / (c.recipient_count * c.step_count)) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    )}
                    <StatusBadge status={c.status as CampaignStatus} />
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Summary */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-lg font-semibold text-gray-900">Overall</h2>
            <p className="mt-1 text-sm text-gray-500">
              {totalSent} total emails sent across {campaigns.length} campaigns
            </p>
          </div>
        </>
      )}
    </div>
  );
}
