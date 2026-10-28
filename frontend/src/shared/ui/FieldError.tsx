import { ApiError } from "../api/client";

/** Відображає DRF-помилку конкретного поля поруч із його input. */
export function FieldError({ error, name }: { error: unknown; name: string }) {
  if (
    !(error instanceof ApiError) ||
    !error.body ||
    typeof error.body !== "object"
  ) return null;
  const value = (error.body as Record<string, unknown>)[name];
  if (!value) return null;
  return (
    <small className="field-error" role="alert">
      {typeof value === "object" ? JSON.stringify(value) : String(value)}
    </small>
  );
}
