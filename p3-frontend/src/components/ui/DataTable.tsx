import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Search, ArrowUpDown } from "lucide-react";
import { cn } from "../../utils/cn";

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  render?: (row: T) => React.ReactNode;
  sortValue?: (row: T) => string | number;
}

export function DataTable<T>({
  data,
  columns,
  searchKeys,
  pageSize = 8,
  emptyLabel = "No records found",
}: {
  data: T[];
  columns: Column<T>[];
  searchKeys?: (keyof T)[];
  pageSize?: number;
  emptyLabel?: string;
}) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    if (!query || !searchKeys) return data;
    const q = query.toLowerCase();
    return data.filter((row) => searchKeys.some((k) => String(row[k] ?? "").toLowerCase().includes(q)));
  }, [data, query, searchKeys]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const col = columns.find((c) => c.key === sortKey);
    if (!col) return filtered;
    const arr = [...filtered];
    arr.sort((a, b) => {
      const va = col.sortValue ? col.sortValue(a) : "";
      const vb = col.sortValue ? col.sortValue(b) : "";
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return arr;
  }, [filtered, sortKey, sortDir, columns]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const pageRows = sorted.slice(page * pageSize, page * pageSize + pageSize);

  return (
    <div>
      {searchKeys && (
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="relative max-w-xs flex-1">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-300" />
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
              placeholder="Search…"
              className="h-9 w-full rounded-xl border border-ink-100 bg-white pl-8 pr-3 text-xs outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
            />
          </div>
          <span className="text-xs text-ink-500">{sorted.length} records</span>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-ink-100">
        <table className="w-full text-sm">
          <thead className="bg-bg-soft">
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  onClick={() => {
                    if (!c.sortValue) return;
                    if (sortKey === c.key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                    else {
                      setSortKey(c.key);
                      setSortDir("asc");
                    }
                  }}
                  className={cn(
                    "px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-ink-500",
                    c.align === "right" ? "text-right" : "text-left",
                    c.sortValue && "cursor-pointer select-none hover:text-ink-700"
                  )}
                >
                  <span className="inline-flex items-center gap-1">
                    {c.header}
                    {c.sortValue && <ArrowUpDown className="h-3 w-3" />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100">
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-10 text-center text-xs text-ink-500">
                  {emptyLabel}
                </td>
              </tr>
            ) : (
              pageRows.map((row, i) => (
                <tr key={i} className="hover:bg-bg-soft/60 transition-colors">
                  {columns.map((c) => (
                    <td key={c.key} className={cn("px-4 py-2.5 text-ink-700", c.align === "right" && "text-right")}>
                      {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? "—")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-ink-500">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-ink-100 text-ink-500 disabled:opacity-40 hover:bg-bg-soft"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-ink-100 text-ink-500 disabled:opacity-40 hover:bg-bg-soft"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
