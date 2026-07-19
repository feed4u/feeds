import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { ThemeProvider } from "next-themes";
import { ScrollToTop } from "@/components/ScrollToTop";
import { SearchProvider } from "@/contexts/SearchContext";
import { vertical } from "@/config/verticals";
import { lazy, Suspense } from "react";
import Index from "./pages/Index";
import Archive from "./pages/Archive";
import NotFound from "./pages/NotFound";

const MorningCall = lazy(() => import("./pages/MorningCall"));
const Trends = lazy(() => import("./pages/Trends"));
const ThreatActorTaxonomy = lazy(() => import("./pages/ThreatActorTaxonomy"));
const ThreatActorDetail = lazy(() => import("./pages/ThreatActorDetail"));
const Duplicates = lazy(() => import("./pages/Duplicates"));

const queryClient = new QueryClient();

const App = () => (
  <HelmetProvider>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <TooltipProvider>
          <SearchProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter
            future={{
              v7_startTransition: true,
              v7_relativeSplatPath: true,
            }}
          >
            <ScrollToTop />
            <Suspense fallback={null}>
              <Routes>
                <Route path="/" element={<Index />} />
                <Route path="/archive" element={<Archive />} />
                {vertical.features.morningCall && (
                  <Route path="/morning-call" element={<MorningCall />} />
                )}
                {vertical.features.trends && (
                  <Route path="/trends" element={<Trends />} />
                )}
                {vertical.features.threatActors && (
                  <>
                    <Route path="/threat-actor/:actorName" element={<ThreatActorDetail />} />
                    <Route path="/threat-actors/:taxonomyId" element={<ThreatActorTaxonomy />} />
                  </>
                )}
                {vertical.features.duplicates && (
                  <Route path="/duplicates" element={<Duplicates />} />
                )}
                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
          </SearchProvider>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </HelmetProvider>
);

export default App;
