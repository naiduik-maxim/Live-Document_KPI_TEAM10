import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useUser } from "../../features/auth/context/SessionContext";
import { Registry } from "../../features/documents/pages/Registry";
import { CreateDocument } from "../../features/documents/pages/CreateDocument";
import { DocumentDetail } from "../../features/documents/pages/DocumentDetail";
import { Templates } from "../../features/templates/pages/Templates";
import { AnalyticsPage } from "../../features/analytics/pages/AnalyticsPage";
import { UsersAdmin } from "../../features/admin/pages/UsersAdmin";
import { TemplateAdmin } from "../../features/admin/pages/TemplateAdmin";

/** Маршрути авторизованої частини; API повторно перевіряє права на сервері. */
export function AppRoutes() {
  const user = useUser();
  return (
    <Routes>
      <Route path="/" element={<AnalyticsPage />} />
      <Route path="/documents" element={<Registry />} />
      <Route path="/archive" element={<Registry archive />} />
      <Route path="/templates" element={<Templates />} />
      <Route
        path="/templates/:id/create"
        element={<CreateDocument />}
      />
      <Route path="/documents/:id" element={<DocumentDetail />} />
      <Route
        path="/users"
        element={
          user.role === "admin" ? <UsersAdmin /> : <Navigate to="/" />
        }
      />
      <Route
        path="/template-admin"
        element={
          user.role === "admin" ? (
            <TemplateAdmin />
          ) : (
            <Navigate to="/" />
          )
        }
      />
      <Route path="/login" element={<Navigate to="/" />} />
      <Route
        path="*"
        element={
          <div>
            <h1>Сторінку не знайдено</h1>
            <Link to="/">Повернутися до огляду</Link>
          </div>
        }
      />
    </Routes>
  );
}
