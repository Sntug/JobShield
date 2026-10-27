import type { ReactNode } from "react";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";
import { AuthProvider } from "@/providers/auth-provider";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi" className={cn("font-sans", geist.variable)}>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
