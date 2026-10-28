import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../shared/api/client";
import { ErrorBox, Heading, Loading } from "../../../shared/ui";
import { FieldError } from "../../../shared/ui/FieldError";
import { Pagination } from "../../../shared/ui/Pagination";
import { roles, type User, type Page } from "../../../shared/types";

/** Адміністративна форма; права та допустимі ролі додатково перевіряє Backend. */
export function UsersAdmin() {
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const list = useQuery({
    queryKey: ["users", page],
    queryFn: () => api<Page<User>>(`users/?page=${page}`),
  });
  const [selected, setSelected] = useState<User | null>(null);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  return (
    <>
      <Heading
        title="Користувачі"
        description="Облікові записи та ролі кафедри."
      />
      <ErrorBox error={list.error || error} />
      <section className="panel">
        <h2>{selected ? "Редагування користувача" : "Новий користувач"}</h2>
        <form
          key={selected?.id || "new"}
          className="admin-form"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError(undefined);
            const form = e.currentTarget;
            const values = new FormData(form);
            const body: Record<string, unknown> = Object.fromEntries(
              values.entries(),
            );
            body.is_active = values.get("is_active") === "on";
            if (!body.password) delete body.password;
            try {
              await api(
                selected ? `users/${selected.id}/` : "users/",
                selected ? "PATCH" : "POST",
                body,
              );
              setSelected(null);
              await client.invalidateQueries({ queryKey: ["users"] });
              form.reset();
            } catch (err) {
              setError(err);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Логін
            <input name="username" required defaultValue={selected?.username} />
            <FieldError error={error} name="username" />
          </label>
          <label>
            Пароль{selected ? " (залиште порожнім без зміни)" : ""}
            <input
              name="password"
              type="password"
              required={!selected}
              minLength={8}
              autoComplete="new-password"
            />
            <FieldError error={error} name="password" />
          </label>
          <label>
            Ім’я
            <input name="first_name" defaultValue={selected?.first_name} />
            <FieldError error={error} name="first_name" />
          </label>
          <label>
            Прізвище
            <input name="last_name" defaultValue={selected?.last_name} />
            <FieldError error={error} name="last_name" />
          </label>
          <label>
            Email
            <input name="email" type="email" defaultValue={selected?.email} />
            <FieldError error={error} name="email" />
          </label>
          <label>
            Роль
            <select name="role" defaultValue={selected?.role || "teacher"}>
              {Object.entries(roles).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
            <FieldError error={error} name="role" />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              name="is_active"
              defaultChecked={selected?.is_active ?? true}
            />
            Активний користувач
          </label>
          <div className="actions">
            <button className="primary" disabled={busy}>
              {busy ? "Збереження…" : "Зберегти користувача"}
            </button>
            {selected && (
              <button type="button" onClick={() => setSelected(null)}>
                Скасувати
              </button>
            )}
          </div>
        </form>
      </section>
      <section className="panel spaced">
        {list.isLoading ? (
          <Loading />
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Логін</th>
                    <th>Ім’я</th>
                    <th>Роль</th>
                    <th>Доступ</th>
                    <th>Дії</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data?.results.map((user) => (
                    <tr key={user.id}>
                      <td>{user.username}</td>
                      <td>
                        {user.first_name} {user.last_name}
                      </td>
                      <td>{roles[user.role]}</td>
                      <td>{user.is_active ? "Активний" : "Заблокований"}</td>
                      <td>
                        <button
                          onClick={() => {
                            setSelected(user);
                            window.scrollTo({ top: 0, behavior: "smooth" });
                          }}
                        >
                          Редагувати {user.username}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={page}
              count={list.data?.count || 0}
              onChange={setPage}
            />
          </>
        )}
      </section>
    </>
  );
}
