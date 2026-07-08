import React, { useState } from "react";
import { FileText, ClipboardPaste, Globe, SquarePlay, Mic } from "lucide-react";
import { api } from "../api";

const TABS = [
  { key: "pdf", label: "Upload Document", icon: <FileText size={14} /> },
  { key: "text", label: "Paste text", icon: <ClipboardPaste size={14} /> },
  { key: "url", label: "Web page", icon: <Globe size={14} /> },
  { key: "youtube", label: "YouTube", icon: <SquarePlay size={14} /> },
  { key: "audio", label: "Audio", icon: <Mic size={14} /> },
];

const ACCEPT_BY_TAB = {
  pdf: "application/pdf,.pdf,.docx",
  audio: ".mp3,.wav,.m4a,.ogg,.webm,.flac,.aac",
};

const UploadPanel = ({ onUploaded }) => {
  const [tab, setTab] = useState("pdf");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [pastedText, setPastedText] = useState("");
  const [url, setUrl] = useState("");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const resetFields = () => {
    setTitle("");
    setFile(null);
    setPastedText("");
    setUrl("");
    setYoutubeUrl("");
  };

  const handleTabChange = (key) => {
    setTab(key);
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!title.trim()) {
      setError("Please give this document a title.");
      return;
    }

    setUploading(true);

    try {
      if (tab === "pdf") {
        if (!file) {
          setError("Choose a file first.");
          setUploading(false);
          return;
        }
        const formData = new FormData();
        formData.append("file", file);
        formData.append("title", title.trim());
        await api.upload("/documents", formData);
      } else if (tab === "audio") {
        if (!file) {
          setError("Choose an audio file first.");
          setUploading(false);
          return;
        }
        const formData = new FormData();
        formData.append("file", file);
        formData.append("title", title.trim());
        await api.upload("/documents/from-audio", formData);
      } else if (tab === "text") {
        if (!pastedText.trim()) {
          setError("Paste in some text first.");
          setUploading(false);
          return;
        }
        await api.post("/documents/from-text", {
          title: title.trim(),
          text: pastedText,
        });
      } else if (tab === "url") {
        if (!url.trim()) {
          setError("Enter a web page URL first.");
          setUploading(false);
          return;
        }
        await api.post("/documents/from-url", {
          title: title.trim(),
          url,
        });
      } else if (tab === "youtube") {
        if (!youtubeUrl.trim()) {
          setError("Enter a YouTube URL first.");
          setUploading(false);
          return;
        }
        await api.post("/documents/from-youtube", {
          title: title.trim(),
          url: youtubeUrl,
        });
      }

      resetFields();
      onUploaded?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-surface border border-border rounded-xl p-5 mb-10">
      <div className="flex gap-2 mb-4 border-b border-border overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => handleTabChange(t.key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              tab === t.key
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex flex-col sm:flex-row gap-3 sm:items-end"
      >
        <div className="flex-1">
          <label className="block text-sm text-muted mb-1">
            Title <span className="text-incorrect">*</span>
          </label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. COS 211 - Data Structures"
            required
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
          />
        </div>

        {(tab === "pdf" || tab === "audio") && (
          <div className="flex-1">
            <label className="block text-sm text-muted mb-1">
              {tab === "pdf" ? "Document (PDF or Word)" : "Audio file"}
            </label>
            <input
              type="file"
              accept={ACCEPT_BY_TAB[tab]}
              onChange={(e) => setFile(e.target.files[0])}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:bg-accent file:text-bg file:font-medium file:cursor-pointer"
            />
          </div>
        )}

        {tab === "text" && (
          <div className="flex-1">
            <label className="block text-sm text-muted mb-1">
              Paste your notes
            </label>
            <textarea
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              rows={3}
              placeholder="Paste lecture notes, an article, anything you want to be quizzed on..."
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent transition-colors resize-y"
            />
          </div>
        )}

        {tab === "url" && (
          <div className="flex-1">
            <label className="block text-sm text-muted mb-1">
              Web page URL
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/article"
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
            />
          </div>
        )}

        {tab === "youtube" && (
          <div className="flex-1">
            <label className="block text-sm text-muted mb-1">
              YouTube video URL
            </label>
            <input
              type="url"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
            />
          </div>
        )}

        <button
          type="submit"
          disabled={uploading}
          className="bg-accent text-bg font-semibold rounded-lg px-5 py-2 hover:opacity-90 transition-opacity disabled:opacity-50 whitespace-nowrap"
        >
          {uploading
            ? tab === "youtube" || tab === "audio"
              ? "Processing... this can take a minute"
              : "Adding..."
            : "Add"}
        </button>
      </form>

      {tab === "url" && (
        <p className="text-xs text-muted mt-2">
          Works best on articles and docs pages. Pages that need JavaScript to
          load their content aren't supported yet.
        </p>
      )}

      {tab === "youtube" && (
        <p className="text-xs text-muted mt-2">
          Uses the video's captions when available (fast). If there are no
          captions, audio is transcribed instead - this can take noticeably
          longer for long videos.
        </p>
      )}

      {tab === "audio" && (
        <p className="text-xs text-muted mt-2">
          Transcribed via AI. Supports mp3, wav, m4a, ogg, webm, flac, aac up to
          25MB. Longer recordings take longer to process.
        </p>
      )}

      {error && (
        <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2 mt-3">
          {error}
        </p>
      )}
    </div>
  );
};

export default UploadPanel;
