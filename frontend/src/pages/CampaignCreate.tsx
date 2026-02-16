import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateCampaign } from "../api/campaigns";
import FileUpload from "../components/FileUpload";

type Step = 1 | 2 | 3;

export default function CampaignCreate() {
  const navigate = useNavigate();
  const createMutation = useCreateCampaign();

  const [step, setStep] = useState<Step>(1);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [recipientsFile, setRecipientsFile] = useState<File | null>(null);
  const [scheduleFile, setScheduleFile] = useState<File | null>(null);
  const [emailDocument, setEmailDocument] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  function canProceed(): boolean {
    if (step === 1) return name.trim().length > 0;
    if (step === 2) return !!recipientsFile && !!scheduleFile && !!emailDocument;
    return true;
  }

  async function handleSubmit() {
    if (!recipientsFile || !scheduleFile || !emailDocument) return;

    const formData = new FormData();
    formData.append("name", name.trim());
    if (description.trim()) formData.append("description", description.trim());
    formData.append("recipients_file", recipientsFile);
    formData.append("schedule_file", scheduleFile);
    formData.append("email_document", emailDocument);

    setError(null);
    try {
      const campaign = await createMutation.mutateAsync(formData);
      navigate(`/campaigns/${campaign.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create campaign");
    }
  }

  const stepLabels = ["Campaign Info", "Upload Files", "Review & Create"];

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Create Campaign</h1>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {stepLabels.map((label, i) => {
          const stepNum = (i + 1) as Step;
          const isActive = step === stepNum;
          const isDone = step > stepNum;
          return (
            <div key={label} className="flex items-center gap-2">
              {i > 0 && <div className={`h-px w-8 ${isDone ? "bg-blue-600" : "bg-gray-300"}`} />}
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : isDone
                      ? "bg-blue-100 text-blue-700"
                      : "bg-gray-200 text-gray-500"
                }`}
              >
                {isDone ? "\u2713" : stepNum}
              </div>
              <span className={`text-sm ${isActive ? "font-medium text-gray-900" : "text-gray-500"}`}>
                {label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Step content */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Campaign Name *
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Q1 Outreach"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="desc" className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                id="desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                placeholder="Optional campaign description..."
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <FileUpload
              label="Recipients File (CSV/XLSX)"
              accept=".csv,.xlsx"
              file={recipientsFile}
              onFileSelect={setRecipientsFile}
            />
            <FileUpload
              label="Schedule File (CSV/XLSX)"
              accept=".csv,.xlsx"
              file={scheduleFile}
              onFileSelect={setScheduleFile}
            />
            <FileUpload
              label="Email Template (MD/DOCX)"
              accept=".md,.docx"
              file={emailDocument}
              onFileSelect={setEmailDocument}
            />
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h3 className="font-medium text-gray-900">Review</h3>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Name</dt>
                <dd className="font-medium text-gray-900">{name}</dd>
              </div>
              {description && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Description</dt>
                  <dd className="text-gray-900">{description}</dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-gray-500">Recipients file</dt>
                <dd className="text-gray-900">{recipientsFile?.name}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Schedule file</dt>
                <dd className="text-gray-900">{scheduleFile?.name}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Email template</dt>
                <dd className="text-gray-900">{emailDocument?.name}</dd>
              </div>
            </dl>
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}
      </div>

      {/* Navigation buttons */}
      <div className="flex justify-between">
        <button
          onClick={() => step > 1 && setStep((step - 1) as Step)}
          disabled={step === 1}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:invisible"
        >
          Back
        </button>
        {step < 3 ? (
          <button
            onClick={() => canProceed() && setStep((step + 1) as Step)}
            disabled={!canProceed()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={createMutation.isPending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {createMutation.isPending ? "Creating..." : "Create Campaign"}
          </button>
        )}
      </div>
    </div>
  );
}
