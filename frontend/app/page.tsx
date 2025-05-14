"use client";

import { useState, useEffect } from "react";
import { UploadButton } from "@/components/UploadButton";
import { Console } from "@/components/Console";
import { sendTextToBackend, sendTextForDraftResponse, sendTextForKeyInfo} from "@/utils/api";
import Papa from "papaparse";

export default function Home() {
  const [text, setText] = useState("");
  const [summary, setSummary] = useState("");
  const [draftResponse, setDraftResponse] = useState("");
  const [keyInfo, setKeyInfo] = useState("");
  const [icsFile, setIcsFile] = useState("");  
  const [loading, setLoading] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const [keyLoading, setKeyLoading] = useState(false);
  const [userNames, setUserNames] = useState<string[]>([]);
  const [selectedUser, setSelectedUser] = useState("");

  const handleFileUpload = (fileContent: string) => {
    setText(fileContent);
    
    // Extract user names from CSV
    try {
      const parsed = Papa.parse(fileContent, { header: true, skipEmptyLines: true });
      if (parsed.data && parsed.data.length > 0) {
        // Look for user_name column (or alternatives)
        const firstRow = parsed.data[0] as any;
        const userNameKey = 
          Object.keys(firstRow).find(key => 
            ["user_name", "author", "sender"].includes(key.toLowerCase())
          );
        
        if (userNameKey) {
          // Extract unique user names
          const names = Array.from(
            new Set(
              parsed.data
                .map((row: any) => row[userNameKey])
                .filter(name => name && name.trim() !== "")
            )
          ) as string[];
          
          setUserNames(names);
          // Set default selected user
          if (names.length > 0) {
            setSelectedUser(names[0]);
          }
        }
      }
    } catch (error) {
      console.error("Failed to parse user names", error);
    }
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

  const handleDraftResponse = async () => {
    try {
      setDraftLoading(true);
      const result = await sendTextForDraftResponse(text, selectedUser);
      setDraftResponse(result.draft);
    } catch (error) {
      alert("Failed to draft response.");
    } finally {
      setDraftLoading(false);
    }
  };
  const handleGetKeyInfo = async () => {
    if (!text) return;
    setKeyLoading(true);
    const { key_info, ics_file } = await sendTextForKeyInfo(text);
    setKeyInfo(key_info);
    setIcsFile(ics_file);
    setKeyLoading(false);
  };

  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold mb-4">Social Assistant Console</h1>
      <UploadButton onUpload={handleFileUpload} />
      <div className="flex flex-wrap gap-4 mt-4">
      <button
          onClick={handleGetKeyInfo}
          disabled={!text || keyLoading}
          className="p-2 bg-purple-500 text-white rounded disabled:opacity-50"
        >
          {keyLoading ? "Extracting..." : "Get Key Info"}
        </button>
        <button
          onClick={handleSummarize}
          disabled={!text || loading}
          className="p-2 bg-blue-500 text-white rounded disabled:opacity-50"
        >
          {loading ? "Summarizing..." : "Summarize"}
        </button>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleDraftResponse}
            disabled={!text || draftLoading}
            className="p-2 bg-green-500 text-white rounded disabled:opacity-50"
          >
            {draftLoading ? "Drafting..." : "Draft Response"}
          </button>
          
          {userNames.length > 0 && (
            <select 
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="p-2 border rounded"
            >
              {userNames.map(name => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
      <Console text={text} summary={summary} draftResponse={draftResponse} keyInfo={keyInfo} icsFile={icsFile}/>
    </main>
  );
}