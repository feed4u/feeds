import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Shield, Cpu, TrendingUp, Database, Newspaper, Sun, Moon, Search, type LucideIcon } from "lucide-react";
import { useTheme } from "next-themes";
import { Link, useLocation } from "react-router-dom";
import { useSearch } from "@/contexts/SearchContext";
import { vertical } from "@/config/verticals";

const ICONS: Record<typeof vertical.iconName, LucideIcon> = {
  shield: Shield,
  cpu: Cpu,
  "trending-up": TrendingUp,
  database: Database,
  newspaper: Newspaper,
};

const NAV_ITEMS: Array<{ path: string; label: string; enabled: boolean }> = [
  { path: "/morning-call", label: "Daily Report", enabled: vertical.features.morningCall },
  { path: "/archive", label: "Archive", enabled: true },
  { path: "/trends", label: "Trends", enabled: vertical.features.trends },
  { path: "/duplicates", label: "Duplicates", enabled: vertical.features.duplicates },
];

export function Header() {
  const { theme, setTheme } = useTheme();
  const location = useLocation();
  const { searchQuery, setSearchQuery } = useSearch();

  const isActive = (path: string) => location.pathname === path;
  const Icon = ICONS[vertical.iconName];

  return (
    <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="container py-4">
        <div className="flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Icon className="h-8 w-8 text-primary" />
              <span className="text-2xl font-bold font-mono text-glow text-primary">
                {vertical.logoText.primary}<span className="text-foreground">{vertical.logoText.suffix}</span>
              </span>
            </div>
            <Badge variant="live">LIVE FEED</Badge>
          </Link>

          <div className="flex items-center gap-4 flex-1 justify-end">
            <nav className="hidden md:flex items-center gap-6">
              {NAV_ITEMS.filter((item) => item.enabled).map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`text-[15px] font-medium transition-colors ${
                    isActive(item.path) ? 'text-primary' : 'text-muted-foreground hover:text-primary'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            {/* Top bar search */}
            <div className="hidden md:block w-full max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={vertical.searchPlaceholder}
                  className="pl-9 h-9 bg-background border-border font-mono text-[15px]"
                />
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="h-9 w-9"
            >
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>
          </div>
        </div>

        <div className="mt-4 hidden md:block">
          <h1 className="text-[22px] font-semibold text-foreground">
            {vertical.heading}
          </h1>
          <p className="text-[15px] text-muted-foreground mt-1">
            {vertical.tagline}
          </p>
        </div>
      </div>
    </header>
  );
}
