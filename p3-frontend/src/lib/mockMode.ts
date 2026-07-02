type Listener = (active: boolean) => void;

let active = false;
const listeners = new Set<Listener>();

export function setMockMode(value: boolean) {
  if (active === value) return;
  active = value;
  listeners.forEach((l) => l(active));
}

export function getMockMode(): boolean {
  return active;
}

export function subscribeMockMode(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
