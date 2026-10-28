/** Зберігає HTTP-статус і DRF-помилки полів для форм та загальних повідомлень. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(errorMessage(status, body));
  }
}
function flatten(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(flatten).join(" ");
  if (value && typeof value === "object")
    return Object.entries(value)
      .map(([k, v]) => `${k}: ${flatten(v)}`)
      .join(" · ");
  return String(value ?? "");
}
/** Нормалізує detail/field-error map у повідомлення для користувача. */
export function errorMessage(status: number, body: unknown): string {
  const messages: Record<number, string> = {
    401: "Сесія завершилася. Увійдіть знову.",
    403: "Недостатньо прав або сесія CSRF застаріла. Оновіть сторінку.",
    404: "Документ не знайдено або він недоступний.",
    409: "Документ уже змінено. Оновіть його, щоб отримати актуальну версію.",
  };
  return messages[status] || flatten(body) || "Не вдалося виконати запит.";
}
let csrf = "";
/** Отримує свіжий Django CSRF-токен, у тому числі після його ротації при вході. */
export async function ensureCsrf() {
  const response = await fetch("/api/auth/csrf/", {
    credentials: "same-origin",
  });
  const data = await response.json();
  csrf = data.csrfToken;
  return csrf;
}
/** JSON-клієнт одного origin: cookie сесії та CSRF-header для змін, включно з login. */
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  if (method !== "GET") await ensureCsrf();
  const response = await fetch(`/api/${path}`, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(method !== "GET" ? { "X-CSRFToken": csrf } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response
      .json()
      .catch(() => ({ detail: "Помилка зв’язку із сервером." }));
    if (response.status === 401 && !path.startsWith("auth/"))
      window.dispatchEvent(new Event("session-expired"));
    if (response.status === 401 && path === "auth/login/")
      throw new Error("Неправильний логін або пароль, або обліковий запис заблоковано.");
    throw new ApiError(response.status, data);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
