"use client";

import { useState } from "react";
import { UploadButton } from "@/components/UploadButton";
import { Console } from "@/components/Console";
import { sendTextToBackend } from "@/utils/api";

export default function Home() {
  const [text, setText] = useState("");
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFileUpload = (fileContent: string) => {
    setText(fileContent);
  };

  const handleSummarize = async () => {
    try {
      setLoading(true);
      const result = await sendTextToBackend(text);
      setSummary(result.summary);
    } catch (error) {
      alert("Failed to summarize.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold mb-4">Social Assistant Console</h1>
      <UploadButton onUpload={handleFileUpload} />
      <button
        onClick={handleSummarize}
        disabled={!text || loading}
        className="mt-4 p-2 bg-blue-500 text-white rounded disabled:opacity-50"
      >
        {loading ? "Summarizing..." : "Summarize"}
      </button>
      <Console text={text} summary={summary} />
    </main>
  );
}