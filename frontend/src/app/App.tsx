import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Login } from "../features/auth/pages/Login";
import { useSession } from "../features/auth/hooks/useSession";
import { SessionContext } from "../features/auth/context/SessionContext";
import { Loading } from "../shared/ui";
import { AppShell } from "./layout/AppShell";

/** Відновлює сесію перед показом захищених сторінок, зберігаючи прямий URL. */
export function App() {
  const location = useLocation();
  const session = useSession();
  if (session.isLoading) return <Loading />;
  if (!session.data)
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="*"
          element={
            <Navigate
              to="/login"
              replace
              state={{ from: location.pathname + location.search }}
            />
          }
        />
      </Routes>
    );
  return (
    <SessionContext.Provider value={session.data}>
      <AppShell />
    </SessionContext.Provider>
  );
}
