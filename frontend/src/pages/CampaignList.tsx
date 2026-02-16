import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { Link } from "react-router-dom";
import { parseUTC } from "../utils/dates";
import { useCampaigns, useDeleteCampaign } from "../api/campaigns";
import StatusBadge from "../components/StatusBadge";
import type { Campaign, CampaignStatus } from "../types";

const statusFilters: { label: string; value: string | undefined }[] = [
  { label: "All", value: undefined },
  { label: "Draft", value: "draft" },
  { label: "Scheduled", value: "scheduled" },
  { label: "In Progress", value: "in_progress" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
];

const columnHelper = createColumnHelper<Campaign>();

const deletableStatuses = new Set(["draft", "completed", "failed"]);

export default function CampaignList() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const { data, isLoading } = useCampaigns(statusFilter);
  const deleteMutation = useDeleteCampaign();

  const columns = [
    columnHelper.accessor("name", {
      header: "Name",
      cell: (info) => (
        <Link
          to={`/campaigns/${info.row.original.id}`}
          className="font-medium text-blue-600 hover:text-blue-700"
        >
          {info.getValue()}
        </Link>
      ),
    }),
    columnHelper.accessor("status", {
      header: "Status",
      cell: (info) => <StatusBadge status={info.getValue() as CampaignStatus} />,
    }),
    columnHelper.accessor("recipient_count", {
      header: "Recipients",
    }),
    columnHelper.display({
      id: "progress",
      header: "Progress",
      cell: (info) => {
        const c = info.row.original;
        const total = c.recipient_count * c.step_count;
        if (total === 0) return <span className="text-gray-400">-</span>;
        return (
          <div className="flex items-center gap-2">
            <div className="h-2 w-20 rounded-full bg-gray-200">
              <div
                className="h-2 rounded-full bg-blue-600"
                style={{ width: `${Math.round((c.sent_count / total) * 100)}%` }}
              />
            </div>
            <span className="text-xs text-gray-500">
              {c.sent_count}/{total}
            </span>
          </div>
        );
      },
    }),
    columnHelper.accessor("created_at", {
      header: "Created",
      cell: (info) => parseUTC(info.getValue()).toLocaleDateString(),
    }),
    columnHelper.display({
      id: "actions",
      header: "",
      cell: (info) => {
        const c = info.row.original;
        return (
          <div className="flex justify-end gap-2">
            <Link
              to={`/campaigns/${c.id}`}
              className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-100"
            >
              View
            </Link>
            {deletableStatuses.has(c.status) && (
              <button
                onClick={() => setConfirmDelete(c.id)}
                className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50"
              >
                Delete
              </button>
            )}
          </div>
        );
      },
    }),
  ];

  const table = useReactTable({
    data: data?.campaigns ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
        <Link
          to="/campaigns/new"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Create Campaign
        </Link>
      </div>

      {/* Status filter */}
      <div className="flex gap-2">
        {statusFilters.map((f) => (
          <button
            key={f.label}
            onClick={() => setStatusFilter(f.value)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              statusFilter === f.value
                ? "bg-blue-100 text-blue-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : (data?.campaigns ?? []).length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white py-16 text-center">
          <p className="text-gray-500">
            {statusFilter ? "No campaigns with this status." : "No campaigns yet."}
          </p>
          {!statusFilter && (
            <Link
              to="/campaigns/new"
              className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Create your first campaign
            </Link>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      onClick={header.column.getToggleSortingHandler()}
                      className="cursor-pointer px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getIsSorted() === "asc" ? " \u2191" : ""}
                      {header.column.getIsSorted() === "desc" ? " \u2193" : ""}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-gray-200">
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete confirmation dialog */}
      {confirmDelete !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900">Delete Campaign</h3>
            <p className="mt-2 text-sm text-gray-500">
              Are you sure? This action cannot be undone.
            </p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setConfirmDelete(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteMutation.mutate(confirmDelete);
                  setConfirmDelete(null);
                }}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
