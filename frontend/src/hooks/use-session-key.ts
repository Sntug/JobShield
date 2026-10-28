"use client";

import { useSyncExternalStore } from "react";
import { AUTH_CHANGED_EVENT, getAuthToken } from "@/lib/api-client";

function subscribe(listener: () => void) {
  window.addEventListener(AUTH_CHANGED_EVENT, listener);
  return () => window.removeEventListener(AUTH_CHANGED_EVENT, listener);
}

export function useSessionKey() {
  return useSyncExternalStore(subscribe, getAuthToken, () => null);
}
