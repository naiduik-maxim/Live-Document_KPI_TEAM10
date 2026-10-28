import { createContext, useContext } from "react";
import type { User } from "../../../shared/types";

// Контекст не імпортує сторінки: features не залежать від app та її маршрутів.
export const SessionContext = createContext<User | null>(null);

/** Повертає користувача лише всередині захищеної частини застосунку. */
export function useUser(): User {
  const user = useContext(SessionContext);
  if (!user) throw new Error("SessionContext requires an authenticated user.");
  return user;
}
