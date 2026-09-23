import { useLayoutEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Shield, Cpu, TrendingUp, Database, Newspaper, Sun, Moon, Search, X, type LucideIcon } from "lucide-react";
import { useTheme } from "next-themes";
import { Link, useLocation, useNavigate } from "react-router-dom";
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

// Pages whose content responds to the search box. Typing anywhere else takes
// the reader to the feed with their query applied.
const SEARCHABLE_PATHS = new Set(["/", "/archive"]);

export function Header() {
  const { theme, setTheme } = useTheme();
  const headerRef = useRef<HTMLElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { searchQuery, setSearchQuery } = useSearch();

  const isActive = (path: string) => location.pathname === path;
  const Icon = ICONS[vertical.iconName];

  // The header is sticky and its height varies (phone/desktop, with or without
  // the page heading), so publish it as a CSS variable. Anything else that
  // needs to stick directly below it — the feed's filter bar — reads this
  // instead of hard-coding an offset.
  useLayoutEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    const apply = () =>
      document.documentElement.style.setProperty(
        "--app-header-h",
        `${Math.round(el.getBoundingClientRect().height)}px`,
      );
    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const onSearchChange = (value: string) => {
    if (SEARCHABLE_PATHS.has(location.pathname)) {
      setSearchQuery(value);
    } else {
      navigate(value ? `/?q=${encodeURIComponent(value)}` : "/");
    }
  };

  const searchBox = (
    <div className="relative w-full">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        type="search"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder={vertical.searchPlaceholder}
        aria-label="Search stories"
        className="pl-9 pr-9 h-9 bg-background border-border text-[15px]"
      />
      {searchQuery && (
        <button
          type="button"
          onClick={() => onSearchChange("")}
          aria-label="Clear search"
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );

  return (
    <header
      ref={headerRef}
      className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-50"
    >
      <div className="container py-3 md:py-4">
        <div className="flex items-center justify-between gap-3 md:gap-4">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <Icon className="h-7 w-7 md:h-8 md:w-8 text-primary" />
            <span className="text-xl md:text-2xl font-bold font-mono text-glow text-primary">
              {vertical.logoText.primary}<span className="text-foreground">{vertical.logoText.suffix}</span>
            </span>
          </Link>

          <div className="flex items-center gap-3 md:gap-4 flex-1 justify-end min-w-0">
            <nav className="flex items-center gap-4 md:gap-6">
              {NAV_ITEMS.filter((item) => item.enabled).map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`text-[15px] font-medium transition-colors whitespace-nowrap ${
                    isActive(item.path) ? 'text-primary' : 'text-muted-foreground hover:text-primary'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="hidden md:block w-full max-w-md">{searchBox}</div>

            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="h-9 w-9 shrink-0"
            >
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>
          </div>
        </div>

        {/* Phones: search gets its own full-width row instead of disappearing. */}
        <div className="mt-3 md:hidden">{searchBox}</div>

      </div>
    </header>
  );
}
