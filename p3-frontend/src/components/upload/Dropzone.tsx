import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileText, FileSpreadsheet, File as FileIcon, X } from "lucide-react";
import { cn } from "../../utils/cn";

const ACCEPTED = [".pdf", ".csv", ".xlsx"];

function fileIconFor(name: string) {
  if (name.endsWith(".pdf")) return <FileText className="h-5 w-5 text-danger" />;
  if (name.endsWith(".csv") || name.endsWith(".xlsx")) return <FileSpreadsheet className="h-5 w-5 text-success" />;
  return <FileIcon className="h-5 w-5 text-ink-500" />;
}

export function Dropzone({
  onFileSelected,
  uploading,
  progress,
}: {
  onFileSelected: (file: File) => void;
  uploading: boolean;
  progress: number;
}) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const f = files[0];
      const ok = ACCEPTED.some((ext) => f.name.toLowerCase().endsWith(ext));
      if (!ok) return;
      setFile(f);
      onFileSelected(f);
    },
    [onFileSelected]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !uploading && inputRef.current?.click()}
      className={cn(
        "relative flex min-h-[280px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed bg-white p-10 text-center transition-all duration-200",
        dragActive ? "border-primary-500 bg-primary-50/50 scale-[1.005]" : "border-ink-200 hover:border-primary-300 hover:bg-bg-tint/40"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(",")}
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
        Drag &amp; drop a bank statement
      </h3>
      <p className="mt-1 text-sm text-ink-500">
        or click to browse — PDF, CSV or XLSX supported
      </p>

      <AnimatePresence>
        {file && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mt-6 w-full max-w-sm rounded-xl border border-ink-100 bg-bg-soft p-3 text-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3">
              {fileIconFor(file.name)}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink-900">{file.name}</p>
                <p className="text-xs text-ink-500">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
              {!uploading && (
                <button
                  onClick={() => setFile(null)}
                  className="flex h-7 w-7 items-center justify-center rounded-lg text-ink-400 hover:bg-ink-100"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {uploading && (
              <div className="mt-3">
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
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
