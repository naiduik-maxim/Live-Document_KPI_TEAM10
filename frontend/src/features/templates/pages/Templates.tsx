import { Link } from "react-router-dom";
import { Empty, ErrorBox, Heading, Loading } from "../../../shared/ui";
import { useTemplates } from "../hooks/useTemplates";

/** Каталог активних демонстраційних шаблонів із серверної схеми. */
export function Templates() {
  const list = useTemplates();
  return (
    <>
      <Heading
        title="Бібліотека шаблонів"
        description="Оберіть основу — система підкаже, які поля потрібно заповнити."
      />
      <div className="notice">
        Демонстраційні приклади. Ці бланки не є офіційними документами кафедри.
      </div>
      <ErrorBox error={list.error} />
      {list.isLoading ? (
        <Loading />
      ) : (
        <div className="template-grid">
          {list.data
            ?.filter((t) => t.is_active)
            .map((t, index) => (
              <article className="panel template-card" key={t.id}>
                <div className="template-icon">
                  {["▤", "▧", "▦", "◴", "◇"][index % 5]}
                </div>
                <span className="small muted">
                  Приклад · версія {t.version}
                </span>
                <h2>{t.name}</h2>
                <p className="muted">{t.description}</p>
                <div className="template-bottom">
                  <span className="small">{t.schema.length} полів</span>
                  <Link className="button" to={`/templates/${t.id}/create`}>
                    Використати →
                  </Link>
                </div>
              </article>
            ))}
        </div>
      )}
      {list.data?.filter((t) => t.is_active).length === 0 && (
        <Empty>Активних шаблонів поки немає.</Empty>
      )}
    </>
  );
}
