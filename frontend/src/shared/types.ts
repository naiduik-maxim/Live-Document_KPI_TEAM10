/** DTO контракту /api/; авторизацію завжди перевіряє сервер. */
export type Role = "teacher" | "manager" | "admin";
export type User = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  role: Role;
  is_active: boolean;
};
/** Декларативне поле шаблону: дані для форми, без HTML чи виконуваних виразів. */
export type Field = {
  name: string;
  label: string;
  type: "text" | "textarea" | "number" | "date" | "select";
  required: boolean;
  max_length?: number;
  min?: number;
  max?: number;
  choices?: string[];
};
export type Template = {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  version: number;
  schema: Field[];
};
export type Status =
  | "draft"
  | "submitted"
  | "returned"
  | "approved"
  | "completed";
export type DocEvent = {
  id: number;
  actor: User;
  from_status: Status;
  to_status: Status;
  comment: string;
  created_at: string;
};
/** Збережений snapshot визначає поля старого документа незалежно від каталогу. */
export type Document = {
  id: number;
  title: string;
  owner: User;
  template: number;
  template_snapshot: Pick<
    Template,
    "name" | "description" | "version" | "schema"
  >;
  data: Record<string, string | number>;
  status: Status;
  version: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  age_seconds: number;
  events: DocEvent[];
};
/** Стандартна DRF-пагінація; next/previous можуть бути абсолютними URL. */
export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
export type Analytics = {
  total: number;
  by_status: Record<Status, number>;
  pending_approval: number;
  completed_in_period: number;
  average_cycle_seconds: number | null;
  creation_trend: { date: string; count: number }[];
};
export const statuses: Record<Status, string> = {
  draft: "Чернетка",
  submitted: "На погодженні",
  returned: "На доопрацюванні",
  approved: "Затверджено",
  completed: "Завершено",
};
export const roles: Record<Role, string> = {
  teacher: "Викладач",
  manager: "Керівник",
  admin: "Адміністратор",
};
