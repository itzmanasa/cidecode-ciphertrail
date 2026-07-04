import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Network,
  Repeat,
  ShieldAlert,
  Receipt,
  FileText,
  FolderClock,
  Settings as SettingsIcon,
  ChevronsLeft,
  ChevronsRight,
  ShieldCheck,
  GitBranch,
} from "lucide-react";
import { cn } from "../../utils/cn";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/money-flow", label: "Money Flow", icon: Network },
  { to: "/money-trail", label: "Money Trail", icon: GitBranch },
  { to: "/round-tripping", label: "Round Tripping", icon: Repeat },
  { to: "/findings", label: "Investigation Findings", icon: ShieldAlert },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/evidence-report", label: "Evidence Report", icon: FileText },
  { to: "/cases", label: "Uploaded Cases", icon: FolderClock },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-30 h-screen border-r border-ink-100 bg-white/80 glass flex flex-col transition-all duration-200",
        collapsed ? "w-[72px]" : "w-[248px]"
      )}
    >
      <div className="flex items-center gap-2.5 px-4 h-16 border-b border-ink-100">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-grad-primary text-white shadow-glow">
          <ShieldCheck className="h-5 w-5" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="text-sm font-bold leading-tight text-ink-900 truncate">CipherTrail</p>
            <p className="text-[10px] font-medium text-ink-500 truncate">Forensic Investigation</p>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary-50 text-primary-700"
                  : "text-ink-700 hover:bg-ink-100/60"
              )
            }
          >
            <item.icon className="h-[18px] w-[18px] shrink-0" />
            {!collapsed && <span className="truncate">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={onToggle}
        className="m-3 flex items-center justify-center gap-2 rounded-xl border border-ink-100 bg-white py-2 text-xs font-medium text-ink-500 hover:bg-ink-100/50 transition-colors"
      >
        {collapsed ? <ChevronsRight className="h-4 w-4" /> : <><ChevronsLeft className="h-4 w-4" /> Collapse</>}
      </button>
    </aside>
  );
}
