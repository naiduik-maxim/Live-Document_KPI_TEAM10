import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../../../shared/api/client";
import { Badge, Empty, ErrorBox, Heading, Loading } from "../../../shared/ui";
import { Pagination } from "../../../shared/ui/Pagination";
import { date, duration } from "../../../shared/utils/format";
import { statuses, type Document, type Page } from "../../../shared/types";
import { useTemplates } from "../../templates/hooks/useTemplates";

/** Серверний реєстр та архів; URL зберігає фільтри для прямих посилань. */
export function Registry({ archive = false }: { archive?: boolean }) {
  const [params, setParams] = useSearchParams();
  const templates = useTemplates();
  // URL — джерело фільтрів: refresh/back/direct link відтворюють той самий запит.
  const query = new URLSearchParams(params);
  if (archive) query.set("status", "completed");
  const list = useQuery({
    queryKey: ["documents", query.toString()],
    queryFn: () => api<Page<Document>>(`documents/?${query}`),
  });
  function filter(name: string, value: string) {
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      if (value) next.set(name, value);
      else next.delete(name);
      // Після звуження фільтра стара сторінка могла б вийти за межі результатів.
      next.delete("page");
      return next;
    });
  }
  return (
    <>
      <Heading
        title={archive ? "Архів документів" : "Реєстр документів"}
        description={
          archive
            ? "Завершені документи та їхня історія."
            : "Створюйте, погоджуйте та відстежуйте документи кафедри."
        }
      >
        <Link className="button primary" to="/templates">
          ＋ Створити документ
        </Link>
      </Heading>
      <section className="panel">
        <div className="filters">
          <label className="search">
            Пошук
            <input
              placeholder="Назва, автор або тип документа"
              value={params.get("search") || ""}
              onChange={(e) => filter("search", e.target.value)}
            />
          </label>
          {!archive && (
            <label>
              Статус
              <select
                value={params.get("status") || ""}
                onChange={(e) => filter("status", e.target.value)}
              >
                <option value="">Усі статуси</option>
                {Object.entries(statuses).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            Шаблон
            <select
              value={params.get("template") || ""}
              onChange={(e) => filter("template", e.target.value)}
            >
              <option value="">Усі шаблони</option>
              {templates.data?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Від дати
            <input
              type="date"
              value={params.get("created_from") || ""}
              onChange={(e) => filter("created_from", e.target.value)}
            />
          </label>
          <label>
            До дати
            <input
              type="date"
              value={params.get("created_to") || ""}
              onChange={(e) => filter("created_to", e.target.value)}
            />
          </label>
          <label>
            Сортування
            <select
              value={params.get("ordering") || "-created_at"}
              onChange={(e) => filter("ordering", e.target.value)}
            >
              <option value="-created_at">Спочатку нові</option>
              <option value="created_at">Спочатку старі</option>
              <option value="title">За назвою</option>
              <option value="-updated_at">Нещодавно змінені</option>
            </select>
          </label>
        </div>
        <ErrorBox error={list.error} />
        {list.isLoading ? (
          <Loading />
        ) : list.data?.results.length ? (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Документ</th>
                    <th>Автор</th>
                    <th>Статус</th>
                    <th>Створено · Київ</th>
                    <th>Вік</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.results.map((doc) => (
                    <tr key={doc.id}>
                      <td>
                        <Link
                          className="document-title"
                          to={`/documents/${doc.id}`}
                        >
                          {doc.title}
                        </Link>
                        <small>{doc.template_snapshot.name}</small>
                      </td>
                      <td>
                        {doc.owner.first_name || doc.owner.username}{" "}
                        {doc.owner.last_name}
                      </td>
                      <td>
                        <Badge status={doc.status} />
                      </td>
                      <td>{date(doc.created_at)}</td>
                      <td>{duration(doc.age_seconds)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={Number(params.get("page") || 1)}
              count={list.data.count}
              onChange={(page) =>
                setParams((previous) => {
                  const next = new URLSearchParams(previous);
                  next.set("page", String(page));
                  return next;
                })
              }
            />
          </>
        ) : (
          !list.error && (
            <Empty>
              Документів за цими умовами немає. Змініть фільтри або створіть
              перший документ.
            </Empty>
          )
        )}
      </section>
    </>
  );
}
