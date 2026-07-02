import { Component, type ErrorInfo, type ReactNode } from "react";
import { ShieldAlert, RotateCcw } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("CipherTrail crashed:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-bg px-6">
          <div className="max-w-md text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-danger-50 text-danger">
              <ShieldAlert className="h-7 w-7" />
            </div>
            <h1 className="text-lg font-bold text-ink-900">Something went wrong</h1>
            <p className="mt-2 text-sm text-ink-500">
              CipherTrail hit an unexpected error while rendering this page. Reloading usually
              fixes it — if it keeps happening, the underlying data for this case may be in an
              unexpected shape.
            </p>
            <p className="mt-3 rounded-lg bg-bg-soft px-3 py-2 font-mono text-xs text-ink-500">
              {this.state.error.message}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-grad-primary px-4 py-2.5 text-sm font-medium text-white shadow-glow hover:opacity-95 transition-opacity"
            >
              <RotateCcw className="h-4 w-4" /> Reload CipherTrail
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
