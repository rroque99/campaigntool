import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useState } from "react";
import { useRecipients } from "../api/campaigns";
import StatusBadge from "./StatusBadge";
import type { EmailStatus, Recipient } from "../types";

interface RecipientTableProps {
  campaignId: number;
  onSelectRecipient?: (recipient: Recipient) => void;
}

const columnHelper = createColumnHelper<Recipient>();

export default function RecipientTable({ campaignId, onSelectRecipient }: RecipientTableProps) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const pageSize = 20;

  const { data, isLoading } = useRecipients(campaignId, {
    page,
    page_size: pageSize,
    search: search || undefined,
    status: statusFilter,
  });

  const columns = [
    columnHelper.accessor("name", {
      header: "Name",
      cell: (info) => info.getValue() ?? "-",
    }),
    columnHelper.accessor("email", {
      header: "Email",
    }),
    columnHelper.accessor("email_status", {
      header: "Status",
      cell: (info) => {
        const s = info.getValue();
        return s ? <StatusBadge status={s as EmailStatus} /> : <span className="text-gray-400">-</span>;
      },
    }),
  ];

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="space-y-4">
      {/* Search and filter */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search by name or email..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <select
          value={statusFilter ?? ""}
          onChange={(e) => {
            setStatusFilter(e.target.value || undefined);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="scheduled">Scheduled</option>
          <option value="sent">Sent</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        {data && (
          <span className="text-sm text-gray-500">{data.total} recipients</span>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      ) : (data?.items.length ?? 0) === 0 ? (
        <p className="py-8 text-center text-sm text-gray-500">No recipients found.</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => onSelectRecipient?.(row.original)}
                  className={onSelectRecipient ? "cursor-pointer hover:bg-blue-50" : "hover:bg-gray-50"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="whitespace-nowrap px-4 py-2.5 text-sm text-gray-700">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
