import { ReactNode } from "react";
import { Header } from "./Header";
import { vertical } from "@/config/verticals";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background gradient-cyber">
      <div className="fixed inset-0 scanline pointer-events-none opacity-50" />

      <Header />

      <main className="container py-6 relative z-10">
        {children}
      </main>

      <footer className="border-t border-border bg-card/50 py-6 mt-12 relative z-10">
        <div className="container">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-[15px] text-muted-foreground">
            <p className="font-mono">
              © {new Date().getFullYear()} {vertical.footerText}
            </p>
            <p className="font-mono text-[13px]">
              Powered by public RSS feeds • Updated every 15 minutes
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
