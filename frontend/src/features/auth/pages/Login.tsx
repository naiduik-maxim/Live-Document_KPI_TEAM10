import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "../../../shared/api/client";
import { ErrorBox } from "../../../shared/ui";
import type { User } from "../../../shared/types";

/** Встановлює Django-сесію й відновлює маршрут, відкритий до входу. */
export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const client = useQueryClient();
  const [error, setError] = useState<unknown>();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<{ username: string; password: string }>({
    resolver: zodResolver(
      z.object({
        username: z.string().min(1, "Вкажіть логін"),
        password: z.string().min(1, "Вкажіть пароль"),
      }),
    ),
  });
  return (
    <main className="login">
      <section className="login-intro">
        <div className="brand-mark">ІПЗЕ</div>
        <p className="eyebrow">ЄДИНИЙ ПРОСТІР КАФЕДРИ</p>
        <h1>
          Документи,
          <br />
          що рухають
          <br />
          роботу вперед.
        </h1>
        <p>
          Від першої чернетки до затвердження —<br />
          усе в одному просторі.
        </p>
        <span className="login-footer">Живі документи кафедри ІПЗЕ</span>
      </section>
      <section className="login-card">
        <p className="eyebrow">РАДІ БАЧИТИ ВАС</p>
        <h2>Вхід у робочий простір</h2>
        <p className="muted">Використайте обліковий запис кафедри.</p>
        <form
          className="form-stack"
          onSubmit={handleSubmit(async (values) => {
            setError(undefined);
            try {
              const user = await api<User>("auth/login/", "POST", values);
              // Приватний cache попереднього облікового запису не переходить у нову сесію.
              client.clear();
              client.setQueryData(["me"], user);
              navigate(
                (location.state as { from?: string } | null)?.from || "/",
              );
            } catch (e) {
              setError(e);
            }
          })}
          noValidate
        >
          <ErrorBox error={error} />
          <label>
            Логін
            <input autoComplete="username" {...register("username")} />
            {errors.username && (
              <small className="field-error">{errors.username.message}</small>
            )}
          </label>
          <label>
            Пароль
            <input
              type="password"
              autoComplete="current-password"
              {...register("password")}
            />
            {errors.password && (
              <small className="field-error">{errors.password.message}</small>
            )}
          </label>
          <button className="primary" disabled={isSubmitting}>
            {isSubmitting ? "Вхід…" : "Увійти"}
          </button>
        </form>
        <p className="small muted">
          Потрібен доступ? Зверніться до адміністратора кафедри.
        </p>
      </section>
    </main>
  );
}
