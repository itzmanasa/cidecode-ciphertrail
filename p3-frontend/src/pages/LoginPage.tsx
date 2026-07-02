import { useState, type FormEvent } from "react";
import { useLocation, useNavigate, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Eye, EyeOff, ShieldCheck, Lock, Mail, Wand2, Loader2 } from "lucide-react";
import { useAuth, DEMO_CREDENTIALS } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import heroImg from "../assets/hero.png";

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    const redirectTo = (location.state as { from?: string } | null)?.from || "/upload";
    return <Navigate to={redirectTo} replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      const redirectTo = (location.state as { from?: string } | null)?.from || "/upload";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const fillDemoCredentials = () => {
    setEmail(DEMO_CREDENTIALS.email);
    setPassword(DEMO_CREDENTIALS.password);
    setError(null);
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2">
      {/* Branding panel */}
      <div className="relative hidden lg:flex flex-col justify-between bg-grad-primary px-12 py-10 text-white overflow-hidden">
        <div className="relative z-10 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/15 ring-1 ring-white/20">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-bold leading-tight">CipherTrail</p>
            <p className="text-[11px] font-medium text-white/70">Forensic Investigation Platform</p>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative z-10 flex flex-1 items-center justify-center py-8"
        >
          <img src={heroImg} alt="" className="max-h-[340px] w-auto drop-shadow-2xl select-none" />
        </motion.div>

        <div className="relative z-10 max-w-md">
          <Badge tone="neutral" className="bg-white/15 text-white ring-white/20 mb-3">
            Karnataka CID · Cyber Crime Investigation Unit
          </Badge>
          <h2 className="text-2xl font-bold leading-tight">
            Trace money flow. Detect round-tripping. Build the case.
          </h2>
          <p className="mt-2 text-sm text-white/70">
            Upload a bank statement to automatically generate an AI-assisted, tamper-evident
            financial forensic investigation brief.
          </p>
        </div>

        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center px-6 py-12 sm:px-12">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm"
        >
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-grad-primary text-white shadow-glow">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-bold leading-tight text-ink-900">CipherTrail</p>
              <p className="text-[10px] font-medium text-ink-500">Forensic Investigation</p>
            </div>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-ink-900">Investigator sign in</h1>
          <p className="mt-1.5 text-sm text-ink-500">
            Sign in with your CID credentials to access active investigations.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-xs font-semibold text-ink-700">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-300" />
                <input
                  id="email"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@cid.karnataka.gov.in"
                  className="w-full rounded-xl border border-ink-100 bg-white py-2.5 pl-9 pr-3 text-sm text-ink-900 placeholder:text-ink-300 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-xs font-semibold text-ink-700">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-300" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••"
                  className="w-full rounded-xl border border-ink-100 bg-white py-2.5 pl-9 pr-10 text-sm text-ink-900 placeholder:text-ink-300 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-700 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <p className="rounded-xl border border-danger/20 bg-danger-50 px-3 py-2 text-xs font-medium text-danger">
                {error}
              </p>
            )}

            <Button type="submit" size="lg" className="w-full" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <div className="mt-4 rounded-xl border border-dashed border-ink-200 bg-bg-soft px-3.5 py-3">
            <p className="text-[11px] font-semibold text-ink-700">Demo mode — no backend required</p>
            <p className="mt-0.5 text-[11px] text-ink-500">
              This build runs entirely on mock data when no CipherTrail backend is reachable.
            </p>
            <button
              type="button"
              onClick={fillDemoCredentials}
              className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-primary-600 hover:text-primary-700"
            >
              <Wand2 className="h-3.5 w-3.5" /> Fill demo credentials
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
