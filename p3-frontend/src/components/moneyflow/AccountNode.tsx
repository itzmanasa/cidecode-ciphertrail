import { Handle, Position } from "reactflow";
import { Landmark } from "lucide-react";
import { cn } from "../../utils/cn";
import { riskColor } from "../../utils/format";

export function AccountNode({ data, selected }: { data: { label: string; risk?: string }; selected: boolean }) {
  const { bg, text, ring } = riskColor(data.risk);
  return (
    <div
      className={cn(
        "min-w-[140px] rounded-xl border bg-white px-3 py-2 shadow-soft transition-shadow",
        selected ? "ring-2 ring-primary-500 border-primary-300" : "border-ink-100"
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-ink-300" />
      <div className="flex items-center gap-2">
        <span className={cn("flex h-6 w-6 items-center justify-center rounded-lg ring-1", bg, text, ring)}>
          <Landmark className="h-3.5 w-3.5" />
        </span>
        <span className="truncate text-xs font-semibold text-ink-900">{data.label}</span>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-ink-300" />
    </div>
  );
}
