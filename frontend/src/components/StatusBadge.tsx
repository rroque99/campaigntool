import type { CampaignStatus, EmailStatus } from "../types";

const styles: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  scheduled: "bg-blue-100 text-blue-700",
  in_progress: "bg-amber-100 text-amber-700 animate-pulse",
  paused: "bg-orange-100 text-orange-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  sent: "bg-green-100 text-green-700",
  pending: "bg-gray-100 text-gray-600",
  cancelled: "bg-gray-100 text-gray-400 line-through",
};

const labels: Record<string, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  in_progress: "In Progress",
  paused: "Paused",
  completed: "Completed",
  failed: "Failed",
  sent: "Sent",
  pending: "Pending",
  cancelled: "Cancelled",
};

export default function StatusBadge({
  status,
}: {
  status: CampaignStatus | EmailStatus;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status] ?? "bg-gray-100 text-gray-700"}`}
    >
      {labels[status] ?? status}
    </span>
  );
}
