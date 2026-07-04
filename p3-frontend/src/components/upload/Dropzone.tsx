import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileText, FileSpreadsheet, File as FileIcon, X } from "lucide-react";
import { cn } from "../../utils/cn";

const ACCEPTED = [".pdf", ".csv", ".xlsx", ".xls", ".txt"];

function fileIconFor(name: string) {
  if (name.endsWith(".pdf")) return <FileText className="h-5 w-5 text-danger" />;
  if (name.endsWith(".csv") || name.endsWith(".xlsx") || name.endsWith(".xls"))
    return <FileSpreadsheet className="h-5 w-5 text-success" />;
  return <FileIcon className="h-5 w-5 text-ink-500" />;
}

export function Dropzone({
  onFileSelected,
  onFilesSelected,
  uploading,
  progress,
}: {
  onFileSelected?: (file: File) => void;
  onFilesSelected?: (files: File[]) => void;
  uploading: boolean;
  progress: number;
}) {
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (incoming: FileList | null) => {
      if (!incoming || incoming.length === 0) return;
      const valid = Array.from(incoming).filter((f) =>
        ACCEPTED.some((ext) => f.name.toLowerCase().endsWith(ext))
      );
      if (valid.length === 0) return;
      setFiles((prev) => {
        const merged = [...prev, ...valid].filter(
          (f, i, arr) => arr.findIndex((x) => x.name === f.name) === i
        );
        return merged;
      });
    },
    []
  );

  const removeFile = (name: string) =>
    setFiles((prev) => prev.filter((f) => f.name !== name));

  const handleUpload = () => {
    if (files.length === 0 || uploading) return;
    if (files.length === 1 && onFileSelected) {
      onFileSelected(files[0]);
    } else if (onFilesSelected) {
      onFilesSelected(files);
    } else if (onFileSelected) {
      onFileSelected(files[0]);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => !uploading && inputRef.current?.click()}
        className={cn(
          "relative flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed bg-white p-10 text-center transition-all duration-200",
          dragActive
            ? "border-primary-500 bg-primary-50/50 scale-[1.005]"
            : "border-ink-200 hover:border-primary-300 hover:bg-bg-tint/40"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(",")}
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />

        <motion.div
          animate={dragActive ? { y: -4, scale: 1.05 } : { y: 0, scale: 1 }}
          className="flex h-16 w-16 items-center justify-center rounded-2xl bg-grad-primary text-white shadow-glow mb-4"
        >
          <UploadCloud className="h-7 w-7" />
        </motion.div>

        <h3 className="text-base font-semibold text-ink-900">
          Drag &amp; drop bank statements
        </h3>
        <p className="mt-1 text-sm text-ink-500">
          Multiple files supported — PDF, CSV, XLSX, XLS, TXT
        </p>
        {files.length > 0 && (
          <p className="mt-2 text-xs font-semibold text-primary-600">
            {files.length} file{files.length > 1 ? "s" : ""} selected
          </p>
        )}
      </div>

      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-xl border border-ink-100 bg-bg-soft divide-y divide-ink-100"
            onClick={(e) => e.stopPropagation()}
          >
            {files.map((f) => (
              <div key={f.name} className="flex items-center gap-3 px-4 py-2.5">
                {fileIconFor(f.name)}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink-900">{f.name}</p>
                  <p className="text-xs text-ink-500">{(f.size / 1024).toFixed(1)} KB</p>
                </div>
                {!uploading && (
                  <button
                    onClick={() => removeFile(f.name)}
                    className="flex h-7 w-7 items-center justify-center rounded-lg text-ink-400 hover:bg-ink-100"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}

            {uploading && (
              <div className="px-4 py-3">
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
                  <motion.div
                    className="h-full rounded-full bg-grad-primary"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ ease: "easeOut" }}
                  />
                </div>
                <p className="mt-1.5 text-right text-[11px] font-medium text-ink-500">{progress}%</p>
              </div>
            )}

            {!uploading && (
              <div className="px-4 py-3">
                <button
                  onClick={handleUpload}
                  className="w-full rounded-xl bg-grad-primary py-2.5 text-sm font-semibold text-white shadow-glow hover:opacity-90 transition-opacity"
                >
                  {files.length === 1
                    ? "Analyse statement"
                    : `Analyse ${files.length} statements together`}
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}