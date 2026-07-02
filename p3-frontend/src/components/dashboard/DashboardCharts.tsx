import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardHeader, CardTitle, CardDescription } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import type { Analytics } from "../../types";
import { BarChart3 } from "lucide-react";

const COLORS = ["#4F46E5", "#7C3AED", "#22C55E", "#F59E0B", "#EF4444", "#06B6D4"];

function ChartShell({
  title,
  description,
  hasData,
  children,
}: {
  title: string;
  description: string;
  hasData: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <div className="px-3 pb-4">
        {hasData ? (
          <div className="h-[220px] w-full">{children}</div>
        ) : (
          <EmptyState icon={<BarChart3 className="h-7 w-7" />} title="No data available" />
        )}
      </div>
    </Card>
  );
}

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid #E2E8F0",
  fontSize: 12,
  boxShadow: "0 8px 24px -8px rgba(15,23,42,0.15)",
};

export function DashboardCharts({ analytics }: { analytics?: Analytics }) {
  const daily = analytics?.daily_transactions ?? [];
  const debitCredit = analytics?.debit_vs_credit ?? [];
  const txnTypes = analytics?.transaction_types ?? [];
  const cashDigital = analytics?.cash_vs_digital ?? [];
  const timeline = analytics?.timeline ?? [];

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <ChartShell title="Daily Transactions" description="Transaction volume over time" hasData={daily.length > 0}>
        <ResponsiveContainer>
          <LineChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748B" }} />
            <YAxis tick={{ fontSize: 11, fill: "#64748B" }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="count" stroke="#4F46E5" strokeWidth={2.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartShell>

      <ChartShell title="Debit vs Credit" description="Daily inflow against outflow" hasData={debitCredit.length > 0}>
        <ResponsiveContainer>
          <BarChart data={debitCredit}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748B" }} />
            <YAxis tick={{ fontSize: 11, fill: "#64748B" }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="debit" fill="#EF4444" radius={[6, 6, 0, 0]} />
            <Bar dataKey="credit" fill="#22C55E" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartShell>

      <ChartShell title="Transaction Types" description="Distribution by category" hasData={txnTypes.length > 0}>
        <ResponsiveContainer>
          <PieChart>
            <Pie data={txnTypes} dataKey="value" nameKey="type" innerRadius={55} outerRadius={85} paddingAngle={3}>
              {txnTypes.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </ChartShell>

      <ChartShell title="Cash vs Digital" description="Withdrawal method breakdown" hasData={cashDigital.length > 0}>
        <ResponsiveContainer>
          <PieChart>
            <Pie data={cashDigital} dataKey="value" nameKey="name" outerRadius={85}>
              {cashDigital.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </ChartShell>

      <div className="lg:col-span-2">
        <ChartShell title="Activity Timeline" description="Cumulative transaction activity" hasData={timeline.length > 0}>
          <ResponsiveContainer>
            <AreaChart data={timeline}>
              <defs>
                <linearGradient id="timelineFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#7C3AED" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748B" }} />
              <YAxis tick={{ fontSize: 11, fill: "#64748B" }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="value" stroke="#7C3AED" strokeWidth={2.5} fill="url(#timelineFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartShell>
      </div>
    </div>
  );
}
