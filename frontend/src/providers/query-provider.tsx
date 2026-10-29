"use client";

import React, { useState, useEffect, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AUTH_CHANGED_EVENT } from "@/lib/api-client";

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  useEffect(() => {
    const reset = () => {
      void queryClient.cancelQueries();
      queryClient.clear();
    };
    window.addEventListener(AUTH_CHANGED_EVENT, reset);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, reset);
  }, [queryClient]);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
