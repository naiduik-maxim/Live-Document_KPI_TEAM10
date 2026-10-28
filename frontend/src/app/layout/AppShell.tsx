import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, NavLink } from "react-router-dom";
import { api } from "../../shared/api/client";
import { ErrorBox } from "../../shared/ui";
import { roles } from "../../shared/types";
import { useUser } from "../../features/auth/context/SessionContext";
import { AppRoutes } from "../routes/AppRoutes";

/** Спільна навігація та завершення сесії навколо сторінок робочого простору. */
export function AppShell() {
  const user = useUser();
  const client = useQueryClient();
  const [logoutError, setLogoutError] = useState<unknown>();
  const [loggingOut, setLoggingOut] = useState(false);
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-mark">І</span>
          <span>
            Живі документи<small>КАФЕДРА ІПЗЕ</small>
          </span>
        </Link>
        <p className="nav-label">РОБОЧИЙ ПРОСТІР</p>
        <nav aria-label="Головна навігація">
          <NavLink to="/" end>
            ◫ <span>Огляд та аналітика</span>
          </NavLink>
          <NavLink to="/documents">
            ▤ <span>Реєстр документів</span>
          </NavLink>
          <NavLink to="/templates">
            ⊞ <span>Шаблони</span>
          </NavLink>
          <NavLink to="/archive">
            ▣ <span>Архів</span>
          </NavLink>
          {user.role === "admin" && (
            <>
              <p className="nav-label">АДМІНІСТРУВАННЯ</p>
              <NavLink to="/users">
                ♙ <span>Користувачі</span>
              </NavLink>
              <NavLink to="/template-admin">
                ⚙ <span>Керування шаблонами</span>
              </NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-note">
          Менше рутини.
          <br />
          Більше часу для важливого.
        </div>
        <div className="user-card">
          <span className="avatar">
            {(user.first_name || user.username).slice(0, 1).toUpperCase()}
          </span>
          <div>
            <strong>
              {user.first_name || user.username} {user.last_name}
            </strong>
            <small>{roles[user.role]}</small>
          </div>
          <button
            className="icon-button"
            title="Вийти"
            aria-label="Вийти"
            disabled={loggingOut}
            onClick={async () => {
              setLoggingOut(true);
              try {
                await api("auth/logout/", "POST", {});
                // Видаляємо також приватні документи й аналітику минулої сесії.
                client.clear();
                window.location.assign("/login");
              } catch (e) {
                setLogoutError(e);
                setLoggingOut(false);
              }
            }}
          >
            ↗
          </button>
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <span>Цифровий простір кафедри</span>
          <span className="online">
            <i /> Систему підключено
          </span>
        </div>
        <ErrorBox error={logoutError} />
        <div className="content">
          <AppRoutes />
        </div>
      </main>
    </div>

  );
}
