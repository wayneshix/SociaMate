"use client";

export function UploadButton({ onUpload }: { onUpload: (content: string) => void }) {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      onUpload(content);
    };
    reader.readAsText(file);
  };

  return (
    <label className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-gray-400 rounded-lg cursor-pointer hover:border-blue-400 transition">
      <span className="text-gray-500 mb-2">Click or drag a .csv or .txt file here to upload</span>
      <input
        type="file"
        accept=".txt,.csv"
        onChange={handleFileChange}
        className="hidden"
      />
    </label>
  );
}