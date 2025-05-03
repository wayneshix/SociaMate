"use client";

import Papa from "papaparse";

export function Console({ text, summary, keyInfo }: { text: string; summary: string;
  keyInfo: string}) {
  let parsedData: string[][] = [];

  if (text.trim().startsWith("{") || text.trim().startsWith("[")) {
    // JSON handling later if needed
  } else {
    try {
      const parsed = Papa.parse<string[]>(text, { skipEmptyLines: true });
      if (parsed.data && parsed.data.length > 0) {
        parsedData = parsed.data as string[][];
      }
    } catch (error) {
      console.error("CSV parse error", error);
    }
  }

  return (
    <div className="mt-6 flex flex-col gap-8">
      <div>
        <h2 className="text-xl font-semibold mb-2">Original Text</h2>
        {parsedData.length > 0 ? (
          <div className="overflow-x-auto max-h-64 border rounded">
            <table className="min-w-full table-auto text-sm">
              <thead className="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 font-semibold">
                <tr>
                  {parsedData[0].map((header, idx) => (
                    <th key={idx} className="px-4 py-2 border border-gray-300 dark:border-gray-700">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200">
                {parsedData.slice(1).map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    {row.map((cell, i) => (
                      <td key={i} className="px-4 py-2 border border-gray-200 dark:border-gray-700">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <textarea value={text} readOnly className="w-full h-40 border p-2 mt-2" />
        )}
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-2">Summary</h2>
        <textarea value={summary} readOnly className="w-full h-40 border p-2 mt-2" />
      </div>
      <div>
        <h2 className="text-xl font-semibold mb-2">Key Information</h2>
        <textarea value={keyInfo} readOnly className="w-full h-40 border p-2 mt-2" />
      </div>
    </div>
  );
}