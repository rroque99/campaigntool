import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { parseUTC } from "../utils/dates";
import {
  useAddRecipient,
  useAuthStatus,
  useCampaign,
  useCampaignStatus,
  useCancelCampaign,
  useDeleteCampaign,
  useEmailPreview,
  usePauseCampaign,
  useRecipients,
  useScheduleCampaign,
} from "../api/campaigns";
import EmailPreview from "../components/EmailPreview";
import RecipientTable from "../components/RecipientTable";
import StatusBadge from "../components/StatusBadge";
import type { CampaignStatus, Recipient } from "../types";

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const campaignId = Number(id);

  const { data: campaign, isLoading } = useCampaign(campaignId);
  const { data: status } = useCampaignStatus(campaignId);
  const { data: authStatus } = useAuthStatus();

  const scheduleMutation = useScheduleCampaign();
  const pauseMutation = usePauseCampaign();
  const cancelMutation = useCancelCampaign();
  const deleteMutation = useDeleteCampaign();

  const [confirmAction, setConfirmAction] = useState<string | null>(null);
  const [selectedRecipient, setSelectedRecipient] = useState<Recipient | null>(null);
  const [showAddRecipient, setShowAddRecipient] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addName, setAddName] = useState("");
  const [addCustomFields, setAddCustomFields] = useState<Record<string, string>>({});
  const [addError, setAddError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const addRecipientMutation = useAddRecipient(campaignId);

  const { data: previews } = useEmailPreview(
    campaignId,
    selectedRecipient?.id,
  );

  // Get custom field keys from existing recipients
  const { data: recipientsData } = useRecipients(campaignId, { page_size: 1 });
  const customFieldKeys = recipientsData?.items[0]?.custom_fields
    ? Object.keys(recipientsData.items[0].custom_fields)
    : [];

  if (isLoading || !campaign) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  const s = campaign.status;

  async function handleAction(action: string) {
    setConfirmAction(null);
    setActionError(null);
    try {
      if (action === "schedule") await scheduleMutation.mutateAsync(campaignId);
      else if (action === "pause") await pauseMutation.mutateAsync(campaignId);
      else if (action === "cancel") await cancelMutation.mutateAsync(campaignId);
      else if (action === "delete") {
        await deleteMutation.mutateAsync(campaignId);
        navigate("/campaigns");
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action failed");
    }
  }

  async function handleAddRecipient() {
    setAddError(null);
    try {
      const nonEmptyCustomFields: Record<string, string> = {};
      for (const [k, v] of Object.entries(addCustomFields)) {
        if (v.trim()) nonEmptyCustomFields[k] = v.trim();
      }
      await addRecipientMutation.mutateAsync({
        email: addEmail.trim(),
        name: addName.trim() || undefined,
        custom_fields: Object.keys(nonEmptyCustomFields).length > 0
          ? nonEmptyCustomFields
          : undefined,
      });
      setShowAddRecipient(false);
      setAddEmail("");
      setAddName("");
      setAddCustomFields({});
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Failed to add recipient");
    }
  }

  const totalEmails = status?.total_emails ?? campaign.recipient_count * campaign.step_count;
  const sentCount = status?.sent ?? campaign.sent_count;
  const progressPercent = status?.progress_percent ?? (totalEmails > 0 ? (sentCount / totalEmails) * 100 : 0);

  const statCards = [
    { label: "Sent", value: status?.sent ?? campaign.sent_count, color: "text-green-600" },
    { label: "Failed", value: status?.failed ?? campaign.failed_count, color: "text-red-600" },
    { label: "Pending", value: status?.pending ?? campaign.pending_count, color: "text-gray-600" },
    { label: "Scheduled", value: status?.scheduled ?? 0, color: "text-blue-600" },
    { label: "Cancelled", value: status?.cancelled ?? 0, color: "text-gray-400" },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
            <StatusBadge status={s as CampaignStatus} />
          </div>
          {campaign.description && (
            <p className="mt-1 text-sm text-gray-500">{campaign.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          {(s === "draft" || s === "paused") && (
            <button
              onClick={() => setConfirmAction("schedule")}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              {s === "paused" ? "Resume" : "Schedule"}
            </button>
          )}
          {s !== "completed" && s !== "failed" && (
            <button
              onClick={() => setShowAddRecipient(true)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Add Recipient
            </button>
          )}
          {(s === "scheduled" || s === "in_progress") && (
            <button
              onClick={() => setConfirmAction("pause")}
              className="rounded-lg border border-orange-300 px-4 py-2 text-sm font-medium text-orange-700 hover:bg-orange-50"
            >
              Pause
            </button>
          )}
          {(s === "scheduled" || s === "in_progress" || s === "paused") && (
            <button
              onClick={() => setConfirmAction("cancel")}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
            >
              Cancel
            </button>
          )}
          {(s === "draft" || s === "completed" || s === "failed") && (
            <button
              onClick={() => setConfirmAction("delete")}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{actionError}</div>
      )}

      {/* Reply monitoring disabled warning */}
      {authStatus && !authStatus.reply_monitoring_enabled && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
          Automatic reply detection is disabled. Emails will not be automatically cancelled if
          recipients reply. You can manually cancel individual recipients from the recipient list.
        </div>
      )}

      {/* Playwright session expiry warning */}
      {authStatus?.send_backend === "playwright" &&
        !authStatus.playwright_session_active &&
        (s === "paused" || s === "failed") && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm font-medium text-red-800">Gmail session expired</p>
            <p className="mt-1 text-sm text-red-700">
              The Playwright browser session is no longer active. Go to{" "}
              <a href="/settings" className="font-medium underline hover:text-red-900">
                Settings
              </a>{" "}
              to re-login and resume sending.
            </p>
          </div>
        )}

      {/* Progress */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            Progress: {Math.round(progressPercent)}%
          </span>
          <span className="text-sm text-gray-500">
            {sentCount} / {totalEmails} emails
          </span>
        </div>
        <div className="h-3 rounded-full bg-gray-200">
          <div
            className="h-3 rounded-full bg-blue-600 transition-all"
            style={{ width: `${Math.min(progressPercent, 100)}%` }}
          />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
          {statCards.map((c) => (
            <div key={c.label} className="text-center">
              <p className={`text-xl font-semibold ${c.color}`}>{c.value}</p>
              <p className="text-xs text-gray-500">{c.label}</p>
            </div>
          ))}
        </div>
        {status?.next_send_at && (
          <p className="mt-3 text-xs text-gray-500">
            Next send: {parseUTC(status.next_send_at).toLocaleString()}
          </p>
        )}
      </div>

      {/* Recipients */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Recipients</h2>
        <RecipientTable
          campaignId={campaignId}
          onSelectRecipient={setSelectedRecipient}
        />
      </div>

      {/* Email Preview */}
      {selectedRecipient && previews && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              Email Preview &mdash; {selectedRecipient.name ?? selectedRecipient.email}
            </h2>
            <button
              onClick={() => setSelectedRecipient(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Close
            </button>
          </div>
          <EmailPreview previews={previews} />
        </div>
      )}

      {/* Confirm dialog */}
      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 capitalize">
              {confirmAction} Campaign
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              {confirmAction === "delete"
                ? "This will permanently delete the campaign and all its data."
                : `Are you sure you want to ${confirmAction} this campaign?`}
            </p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setConfirmAction(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction(confirmAction)}
                className={`rounded-lg px-4 py-2 text-sm font-medium text-white ${
                  confirmAction === "delete" || confirmAction === "cancel"
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-blue-600 hover:bg-blue-700"
                }`}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Recipient modal */}
      {showAddRecipient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900">Add Recipient</h3>
            <div className="mt-4 space-y-3">
              <div>
                <label htmlFor="recip-email" className="block text-sm font-medium text-gray-700">
                  Email *
                </label>
                <input
                  id="recip-email"
                  type="email"
                  value={addEmail}
                  onChange={(e) => setAddEmail(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label htmlFor="recip-name" className="block text-sm font-medium text-gray-700">
                  Name
                </label>
                <input
                  id="recip-name"
                  type="text"
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              {customFieldKeys.map((key) => (
                <div key={key}>
                  <label
                    htmlFor={`recip-${key}`}
                    className="block text-sm font-medium capitalize text-gray-700"
                  >
                    {key.replace(/_/g, " ")}
                  </label>
                  <input
                    id={`recip-${key}`}
                    type="text"
                    value={addCustomFields[key] ?? ""}
                    onChange={(e) =>
                      setAddCustomFields((prev) => ({ ...prev, [key]: e.target.value }))
                    }
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              ))}
              {addError && (
                <p className="text-sm text-red-600">{addError}</p>
              )}
            </div>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowAddRecipient(false);
                  setAddError(null);
                  setAddCustomFields({});
                }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAddRecipient}
                disabled={!addEmail.trim() || addRecipientMutation.isPending}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {addRecipientMutation.isPending ? "Adding..." : "Add"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
