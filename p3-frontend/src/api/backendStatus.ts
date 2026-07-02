// Once we've learned the real backend is unreachable, skip straight to mock
// data for a while instead of waiting out the timeout again on every single
// query (every page nav would otherwise re-pay that cost).
const COOL_DOWN_MS = 30000;

let knownOffline = false;
let offlineSince = 0;

export function markBackendOffline() {
  knownOffline = true;
  offlineSince = Date.now();
}

export function markBackendOnline() {
  knownOffline = false;
}

export function shouldSkipBackend(): boolean {
  if (!knownOffline) return false;
  if (Date.now() - offlineSince > COOL_DOWN_MS) {
    // Cool-down elapsed — give the real backend another chance.
    knownOffline = false;
    return false;
  }
  return true;
}
