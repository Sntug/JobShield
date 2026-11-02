import type { ReactNode } from "react";
import "./globals.css";
import { cn } from "@/lib/utils";
import { AuthProvider } from "@/providers/auth-provider";
import { QueryProvider } from "@/providers/query-provider";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi" className={cn("font-sans")}>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <QueryProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
