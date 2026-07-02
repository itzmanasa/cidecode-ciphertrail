import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Bell, ShieldHalf, LogOut, ChevronDown, WifiOff } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getMockMode, subscribeMockMode } from "../../lib/mockMode";

export function TopNav() {
  const [now, setNow] = useState(new Date());
  const [menuOpen, setMenuOpen] = useState(false);
  const [mockMode, setMockModeState] = useState(getMockMode());
  const menuRef = useRef<HTMLDivElement>(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => subscribeMockMode(setMockModeState), []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate("/login", { replace: true });
  };

  const initials = (user?.name || "IO")
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-ink-100 bg-white/80 glass px-6">
      <div className="flex items-center gap-2 rounded-lg bg-primary-50 px-2.5 py-1.5">
        <ShieldHalf className="h-4 w-4 text-primary-600" />
        <span className="text-[11px] font-semibold text-primary-700 leading-none">
          Karnataka CID · Cyber Crime Unit
        </span>
      </div>

      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-300" />
          <input
            type="text"
            placeholder="Search case ID, account, IFSC…"
            className="w-full rounded-xl border border-ink-100 bg-bg-soft py-2 pl-9 pr-3 text-sm text-ink-900 placeholder:text-ink-300 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition"
          />
        </div>
      </div>

      <div className="ml-auto flex items-center gap-3">
        {mockMode && (
          <span
            className="hidden md:flex items-center gap-1.5 rounded-lg bg-warning-50 px-2.5 py-1.5 text-[11px] font-semibold text-warning ring-1 ring-warning/15"
            title="No CipherTrail backend reachable — showing local demo data"
          >
            <WifiOff className="h-3.5 w-3.5" /> Offline demo data
          </span>
        )}

        <span className="hidden md:block text-xs font-medium tabular-nums text-ink-500">
          {now.toLocaleString("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </span>

        <button className="relative flex h-9 w-9 items-center justify-center rounded-xl text-ink-500 hover:bg-ink-100/60 transition-colors">
          <Bell className="h-[18px] w-[18px]" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-danger" />
        </button>

        <div className="relative border-l border-ink-100 pl-4" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((o) => !o)}
            className="flex items-center gap-2.5 rounded-xl px-1.5 py-1 hover:bg-ink-100/60 transition-colors"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-grad-primary text-xs font-bold text-white">
              {initials}
            </div>
            <div className="hidden md:block leading-tight text-left">
              <p className="text-xs font-semibold text-ink-900">{user?.name ?? "Investigating Officer"}</p>
              <p className="text-[11px] text-ink-500">{user?.role ?? "CID Cyber Crime Unit"}</p>
            </div>
            <ChevronDown className="hidden md:block h-3.5 w-3.5 text-ink-400" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-2 w-52 overflow-hidden rounded-xl border border-ink-100 bg-white py-1.5 shadow-card animate-fade-in">
              <div className="px-3 py-2 border-b border-ink-100">
                <p className="truncate text-xs font-semibold text-ink-900">{user?.name}</p>
                <p className="truncate text-[11px] text-ink-500">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-danger hover:bg-danger-50 transition-colors"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
