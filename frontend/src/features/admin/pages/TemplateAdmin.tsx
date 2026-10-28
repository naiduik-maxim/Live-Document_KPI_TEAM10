import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../../shared/api/client";
import { ErrorBox, Heading, Loading } from "../../../shared/ui";
import { FieldError } from "../../../shared/ui/FieldError";
import { useTemplates } from "../../templates/hooks/useTemplates";
import type { Template } from "../../../shared/types";

/** Редагує декларативну JSON-схему полів, а не HTML чи виконуваний код. */
export function TemplateAdmin() {
  const client = useQueryClient();
  const list = useTemplates();
  const [selected, setSelected] = useState<Template | null>(null);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  return (
    <>
      <Heading
        title="Керування шаблонами"
        description="Зміни створюють нову версію. Існуючі документи зберігають свій знімок."
      />
      <ErrorBox error={error || list.error} />
      <section className="panel form-panel">
        <h2>{selected ? "Редагувати шаблон" : "Новий шаблон"}</h2>
        <form
          key={selected?.id || "new"}
          className="form-stack"
          onSubmit={async (e) => {
            e.preventDefault();
            setError(undefined);
            setBusy(true);
            const form = e.currentTarget;
            const values = new FormData(form);
            try {
              // JSON.parse перевіряє синтаксис; допустимі поля/обмеження перевіряє API.
              const schema: unknown = JSON.parse(String(values.get("schema")));
              await api(
                selected ? `templates/${selected.id}/` : "templates/",
                selected ? "PATCH" : "POST",
                {
                  name: values.get("name"),
                  description: values.get("description"),
                  is_active: values.get("is_active") === "on",
                  schema,
                },
              );
              setSelected(null);
              await client.invalidateQueries({ queryKey: ["templates"] });
              form.reset();
            } catch (err) {
              setError(
                err instanceof SyntaxError
                  ? new ApiError(400, { schema: ["Схема полів має бути коректним JSON."] })
                  : err,
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Назва шаблону
            <input name="name" defaultValue={selected?.name} required />
            <FieldError error={error} name="name" />
          </label>
          <label>
            Опис
            <textarea name="description" defaultValue={selected?.description} />
            <FieldError error={error} name="description" />
          </label>
          <label>
            Схема полів (JSON)
            <textarea
              className="code-input"
              name="schema"
              rows={12}
              required
              defaultValue={JSON.stringify(
                selected?.schema || [
                  {
                    name: "recipient",
                    label: "Адресат",
                    type: "text",
                    required: true,
                    max_length: 200,
                  },
                ],
                null,
                2,
              )}
            />
            <FieldError error={error} name="schema" />
          </label>
          <p className="small muted">
            Типи: text, textarea, number, date, select. Для select вкажіть
            choices; обмеження: max_length, min, max. HTML та код не
            підтримуються.
          </p>
          <label className="checkbox">
            <input
              type="checkbox"
              name="is_active"
              defaultChecked={selected?.is_active ?? true}
            />
            Активний шаблон
          </label>
          <div className="actions">
            <button className="primary" disabled={busy}>
              {busy ? "Збереження…" : "Зберегти шаблон"}
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
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Шаблон</th>
                  <th>Версія</th>
                  <th>Стан</th>
                  <th>Дії</th>
                </tr>
              </thead>
              <tbody>
                {list.data?.map((t) => (
                  <tr key={t.id}>
                    <td>{t.name}</td>
                    <td>{t.version}</td>
                    <td>{t.is_active ? "Активний" : "Неактивний"}</td>
                    <td>
                      <button
                        onClick={() => {
                          setSelected(t);
                          window.scrollTo({ top: 0, behavior: "smooth" });
                        }}
                      >
                        Редагувати {t.name}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
