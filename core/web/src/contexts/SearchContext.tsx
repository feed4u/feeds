import React, { createContext, useContext, useCallback, ReactNode } from "react";
import { useSearchParams } from "react-router-dom";

// The search query lives in the URL (?q=) so a search can be reloaded,
// bookmarked or shared, and so the same box drives both / and /archive.

type SearchContextValue = {
  searchQuery: string;
  setSearchQuery: (q: string) => void;
};

const SearchContext = createContext<SearchContextValue | undefined>(undefined);

export function SearchProvider({ children }: { children: ReactNode }) {
  const [params, setParams] = useSearchParams();
  const searchQuery = params.get("q") ?? "";

  const setSearchQuery = useCallback(
    (q: string) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (q) next.set("q", q);
          else next.delete("q");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  return (
    <SearchContext.Provider value={{ searchQuery, setSearchQuery }}>
      {children}
    </SearchContext.Provider>
  );
}

export function useSearch() {
  const ctx = useContext(SearchContext);
  if (!ctx) throw new Error("useSearch must be used within SearchProvider");
  return ctx;
}
