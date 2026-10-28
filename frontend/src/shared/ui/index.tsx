import type { ReactNode } from "react";
import { statuses, type Status } from "../types";
/** Єдині назви та CSS-маркери статусів для реєстру й деталей. */
export function Badge({ status }: { status: Status }) {
  return <span className={`badge ${status}`}>{statuses[status]}</span>;
}
/** Загальна помилка з live-region роллю для допоміжних технологій. */
export function ErrorBox({ error }: { error: unknown }) {
  return error ? (
    <div className="error" role="alert">
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null;
}
/** Порожній результат із контекстним поясненням від сторінки. */
export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="empty">
      <span aria-hidden="true">▤</span>
      <p>{children}</p>
    </div>
  );
}
/** Доступне текстове повідомлення про завантаження. */
export function Loading() {
  return (
    <p role="status" className="loading">
      Завантаження…
    </p>
  );
}
/** Спільний заголовок сторінки та область основної дії. */
export function Heading({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <p className="eyebrow">КАФЕДРА ІПЗЕ</p>
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {children}
    </header>
  );
}
