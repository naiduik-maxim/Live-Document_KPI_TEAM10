import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../shared/api/client";
import type { User } from "../../../shared/types";

/** Єдине джерело стану сесії; cookie та перевірка доступу належать Django. */
export function useSession() {
  const client = useQueryClient();
  const session = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("auth/me/"),
  });
  useEffect(() => {
    // API повідомляє про 401; захищені сторінки одразу знімаються з дерева.
    const handler = () => client.setQueryData(["me"], null);
    window.addEventListener("session-expired", handler);
    return () => window.removeEventListener("session-expired", handler);
  }, [client]);
  return session;
}
