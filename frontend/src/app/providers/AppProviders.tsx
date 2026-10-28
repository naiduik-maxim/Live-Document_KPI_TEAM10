import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

// Один cache на запуск SPA; login/logout очищують його при зміні облікового запису.
const client = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: true } },
});

/** Провайдери інфраструктури; тести можуть підставляти власні router/cache. */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}
