import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../../../shared/api/client";
import { useUser } from "../../auth/context/SessionContext";
import { DocumentForm } from "../components/DocumentForm";
import { Badge, ErrorBox, Heading, Loading } from "../../../shared/ui";
import { date, duration } from "../../../shared/utils/format";
import { statuses, type Document } from "../../../shared/types";

/** Показує snapshot документа, погодження, історію та захищений перегляд. */
export function DocumentDetail() {
  const { id } = useParams();
  const user = useUser();
  const client = useQueryClient();
  const [editing, setEditing] = useState(false);
  // Фіксуємо значення й version на початок редагування: refetch не затирає форму.
  const [editSnapshot, setEditSnapshot] = useState<Document | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const doc = useQuery({
    queryKey: ["document", id],
    queryFn: () => api<Document>(`documents/${id}/`),
    refetchInterval: editing ? false : 30000,
    refetchOnWindowFocus: !editing,
    refetchOnReconnect: !editing,
  });
  const preview = useQuery({
    // Версія в ключі не дозволяє показати HTML попереднього збереження.
    queryKey: ["preview", id, doc.data?.version],
    queryFn: () => api<{ html: string }>(`documents/${id}/preview/`),
    enabled: showPreview,
  });
  async function refresh() {
    // Одна зміна впливає на деталі, фільтровані реєстри/архів та агрегати.
    await Promise.all([
      client.invalidateQueries({ queryKey: ["document", id] }),
      client.invalidateQueries({ queryKey: ["documents"] }),
      client.invalidateQueries({ queryKey: ["analytics"] }),
    ]);
  }
  async function transition(action: string) {
    setBusy(true);
    setError(undefined);
    try {
      const updated = await api<Document>(`documents/${id}/transition/`, "POST", {
        action,
        version: doc.data!.version,
        comment,
      });
      client.setQueryData(["document", id], updated);
      setComment("");
      await refresh();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  if (doc.isLoading) return <Loading />;
  if (!doc.data) return <ErrorBox error={doc.error} />;
  const d = editing && editSnapshot ? editSnapshot : doc.data;
  const own = d.owner.id === user.id;
  const leader = user.role === "manager";
  const editable =
    own && ["draft", "returned"].includes(d.status);
  return (
    <>
      <Link className="back-link" to="/documents">
        ← До реєстру
      </Link>
      <Heading
        title={d.title}
        description={`${d.template_snapshot.name} · версія шаблону ${d.template_snapshot.version}`}
      >
        <Badge status={d.status} />
      </Heading>
      <ErrorBox error={error || doc.error} />
      <div className="detail-grid">
        <section className="panel detail-main">
          <div className="section-heading">
            <h2>Вміст документа</h2>
            <div className="actions">
              {editable && (
                <button
                  disabled={busy}
                  onClick={() => {
                    setEditSnapshot(doc.data!);
                    setEditing(!editing);
                  }}
                >
                  {editing ? "Скасувати редагування" : "Редагувати"}
                </button>
              )}
              <button onClick={() => setShowPreview(!showPreview)}>
                {showPreview ? "Сховати перегляд" : "Попередній перегляд"}
              </button>
              <a className="button" href={`/api/documents/${id}/export/`}>
                ↓ Word
              </a>
            </div>
          </div>
          {editing ? (
            <DocumentForm
              key={`${d.id}-${d.version}`}
              title={d.title}
              data={d.data}
              fields={d.template_snapshot.schema}
              onReload={async () => {
                const latest = await doc.refetch();
                if (latest.error) throw latest.error;
                if (latest.data) {
                  setEditSnapshot(latest.data);
                  if (!["draft", "returned"].includes(latest.data.status))
                    setEditing(false);
                }
              }}
              onSave={async (values) => {
                setBusy(true);
                try {
                  const updated = await api<Document>(`documents/${id}/`, "PATCH", {
                    ...values,
                    version: d.version,
                  });
                  // PATCH повертає нову version: наступний submit не має брати старий cache.
                  client.setQueryData(["document", id], updated);
                  await refresh();
                  setEditing(false);
                } finally {
                  setBusy(false);
                }
              }}
            />
          ) : (
            <dl className="document-data">
              {d.template_snapshot.schema.map((field) => (
                <div key={field.name}>
                  <dt>{field.label}</dt>
                  <dd>{String(d.data[field.name] ?? "—")}</dd>
                </div>
              ))}
            </dl>
          )}
          {showPreview && (
            <div>
              <h3>Попередній перегляд</h3>
              <ErrorBox error={preview.error} />
              {preview.isLoading ? (
                <Loading />
              ) : (
                preview.data && (
                  // HTML екранує Backend; sandbox додатково блокує скрипти й доступ до SPA.
                  <iframe
                    className="preview"
                    title="Попередній перегляд документа"
                    sandbox=""
                    srcDoc={preview.data.html}
                  />
                )
              )}
            </div>
          )}
          <div className="document-actions">
            {own && ["draft", "returned"].includes(d.status) && (
              <button
                className="primary"
                disabled={busy || editing}
                onClick={() => transition("submit")}
              >
                Надіслати на погодження
              </button>
            )}
            {leader && d.status === "submitted" && (
              <>
                <label>
                  Коментар погодження
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Для повернення коментар обов’язковий"
                  />
                </label>
                <div className="actions">
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() => transition("approve")}
                  >
                    Затвердити
                  </button>
                  <button
                    disabled={busy || !comment.trim()}
                    onClick={() => transition("return")}
                  >
                    Повернути на доопрацювання
                  </button>
                </div>
              </>
            )}
            {d.status === "approved" && (own || leader) && (
              <button
                className="primary"
                disabled={busy}
                onClick={() => transition("complete")}
              >
                Завершити документ
              </button>
            )}
            {d.status === "completed" && (
              <p className="notice">
                Цикл завершено. Документ доступний для перегляду та експорту.
              </p>
            )}
          </div>
        </section>
        <aside className="detail-side">
          <section className="panel">
            <h2>Про документ</h2>
            <dl className="meta">
              <dt>Автор</dt>
              <dd>
                {d.owner.first_name || d.owner.username} {d.owner.last_name}
              </dd>
              {["approved", "completed"].includes(d.status) && d.signatories?.manager_name && (
                <>
                  <dt>Затвердив керівник</dt>
                  <dd>{d.signatories.manager_name}</dd>
                </>
              )}
              <dt>Створено</dt>
              <dd>{date(d.created_at)}</dd>
              <dt>Остання зміна</dt>
              <dd>{date(d.updated_at)}</dd>
              <dt>Вік документа</dt>
              <dd>
                {duration(d.age_seconds)}
                {d.status === "completed" ? " · зупинено" : ""}
              </dd>
              <dt>Версія документа</dt>
              <dd>{d.version}</dd>
            </dl>
            <small className="muted">Часовий пояс: Europe/Kyiv</small>
          </section>
          <section className="panel">
            <h2>Історія документа</h2>
            <ol className="timeline">
              {d.events.map((event) => (
                <li key={event.id}>
                  <strong>{statuses[event.to_status] || "Подія"}</strong>
                  <small>{date(event.created_at)}</small>
                  <span>
                    {event.actor?.first_name ||
                      event.actor?.username ||
                      "Система"}
                  </span>
                  {event.comment && <p>{event.comment}</p>}
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </div>
    </>
  );
}
