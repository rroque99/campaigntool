import { useState } from "react";
import type { EmailPreview as EmailPreviewType } from "../types";
import { parseUTC } from "../utils/dates";

interface EmailPreviewProps {
  previews: EmailPreviewType[];
}

export default function EmailPreview({ previews }: EmailPreviewProps) {
  const [selectedStep, setSelectedStep] = useState(0);
  const [showHtml, setShowHtml] = useState(true);

  if (previews.length === 0) {
    return <p className="text-sm text-gray-500">No email previews available.</p>;
  }

  const preview = previews[selectedStep];

  return (
    <div className="space-y-4">
      {/* Step selector */}
      {previews.length > 1 && (
        <div className="flex gap-2">
          {previews.map((p, i) => {
            const isActive = i === selectedStep;
            let colorClass = isActive ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100";
            if (p.status === "sent") {
              colorClass = isActive ? "bg-green-100 text-green-700" : "text-green-600 hover:bg-green-50";
            } else if (p.status === "failed") {
              colorClass = isActive ? "bg-red-100 text-red-700" : "text-red-600 hover:bg-red-50";
            } else if (p.status === "cancelled") {
              colorClass = isActive ? "bg-gray-200 text-gray-500" : "text-gray-400 hover:bg-gray-100";
            } else if (p.status === "scheduled") {
              colorClass = isActive ? "bg-blue-100 text-blue-700" : "text-blue-600 hover:bg-blue-50";
            }
            return (
              <button
                key={i}
                onClick={() => setSelectedStep(i)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium ${colorClass}`}
              >
                Step {p.step_order ?? i + 1}
              </button>
            );
          })}
        </div>
      )}

      {/* Email header */}
      <div className="space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
        <div className="flex gap-2">
          <span className="font-medium text-gray-500">To:</span>
          <span className="text-gray-900">
            {preview.recipient_name
              ? `${preview.recipient_name} <${preview.recipient_email}>`
              : preview.recipient_email}
          </span>
        </div>
        <div className="flex gap-2">
          <span className="font-medium text-gray-500">Subject:</span>
          <span className="text-gray-900">{preview.subject}</span>
        </div>
        {preview.scheduled_at && (
          <div className="flex gap-2">
            <span className="font-medium text-gray-500">Scheduled:</span>
            <span className="text-gray-900">
              {parseUTC(preview.scheduled_at).toLocaleString()}
            </span>
          </div>
        )}
      </div>

      {/* Toggle HTML/Text */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowHtml(true)}
          className={`rounded px-2 py-1 text-xs font-medium ${
            showHtml ? "bg-gray-200 text-gray-800" : "text-gray-500 hover:bg-gray-100"
          }`}
        >
          HTML
        </button>
        <button
          onClick={() => setShowHtml(false)}
          className={`rounded px-2 py-1 text-xs font-medium ${
            !showHtml ? "bg-gray-200 text-gray-800" : "text-gray-500 hover:bg-gray-100"
          }`}
        >
          Plain Text
        </button>
      </div>

      {/* Body */}
      {showHtml ? (
        <iframe
          srcDoc={preview.body_html}
          sandbox=""
          className="h-80 w-full rounded-lg border border-gray-200 bg-white"
          title="Email preview"
        />
      ) : (
        <pre className="h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-800">
          {preview.body_html.replace(/<[^>]*>/g, "")}
        </pre>
      )}
    </div>
  );
}
