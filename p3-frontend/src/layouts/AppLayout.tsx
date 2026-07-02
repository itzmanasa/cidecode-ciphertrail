import { Outlet } from "react-router-dom";
import { useState } from "react";
import { Sidebar } from "../components/layout/Sidebar";
import { TopNav } from "../components/layout/TopNav";
import { cn } from "../utils/cn";

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen flex">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className={cn("flex-1 flex flex-col min-w-0 transition-all duration-200", collapsed ? "ml-[72px]" : "ml-[248px]")}>
        <TopNav />
        <main className="flex-1 px-6 py-6 max-w-[1500px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
