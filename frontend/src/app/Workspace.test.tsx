import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import type { Role, Template, User } from "../shared/types";

function account(role: Role): User {
  return { id: 1, role, username: "olena", first_name: "Олена",
    last_name: "", email: "", is_active: true };
}

const emptyPage = { count: 0, previous: null, next: null, results: [] };
const dashboard = { total: 0, by_status: {}, pending_approval: 0,
  completed_in_period: 0, average_cycle_seconds: null, creation_trend: [] };

// Stub the HTTP boundary; keep the production session, router and forms.
function openPage(path: string, responses: Record<string, () => Response>) {
  const fetchSpy = vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    if (!responses[key]) throw new Error(`Unexpected request: ${key}`);
    return responses[key]();
  });
  vi.stubGlobal("fetch", fetchSpy);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  render(<QueryClientProvider client={client}>
    <MemoryRouter initialEntries={[path]}><App /></MemoryRouter>
  </QueryClientProvider>);
  return fetchSpy;
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("[module1] rejects a bad password, then restores the requested registry after login", async () => {
  const login = vi.fn()
    .mockReturnValueOnce(Response.json({}, { status: 401 }))
    .mockReturnValueOnce(Response.json(account("teacher")));
  const requests = openPage("/documents", {
    "GET /api/auth/me/": () => Response.json({}, { status: 401 }),
    "GET /api/auth/csrf/": () => Response.json({ csrfToken: "test-token" }),
    "POST /api/auth/login/": login,
    "GET /api/templates/?page_size=100": () => Response.json(emptyPage),
    "GET /api/documents/?": () => Response.json(emptyPage),
    "GET /api/documents/?status=completed": () => Response.json(emptyPage),
  });
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Логін"), "olena");
  const password = screen.getByLabelText("Пароль");
  await user.type(password, "wrong");
  await user.click(screen.getByRole("button", { name: "Увійти" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Неправильний логін або пароль");
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  await user.clear(password);
  await user.type(password, "correct");
  await user.click(screen.getByRole("button", { name: "Увійти" }));
  expect(requests).toHaveBeenCalledWith("/api/auth/login/", expect.objectContaining({
    method: "POST", body: JSON.stringify({ username: "olena", password: "correct" }),
  }));
  expect(await screen.findByRole("heading", { name: "Реєстр документів" })).toBeVisible();
  expect(screen.getByLabelText("Пошук")).toBeVisible();
  await user.click(screen.getByRole("link", { name: /Архів/ }));
  expect(await screen.findByRole("heading", { name: "Архів документів" })).toBeVisible();
  expect(screen.queryByLabelText("Статус")).not.toBeInTheDocument();
});

it.each([
  ["teacher", "Викладач", "/users"],
  ["manager", "Керівник", "/template-admin"],
] as const)("[module1] guards a direct administrative URL for %s", async (role, label, url) => {
  openPage(url, {
    "GET /api/auth/me/": () => Response.json(account(role)),
    "GET /api/analytics/?date_from=&date_to=": () => Response.json(dashboard),
  });
  expect(await screen.findByRole("heading", { name: "Огляд робочого простору" })).toBeVisible();
  expect(screen.getByText(label)).toBeVisible();
  expect(screen.queryByRole("link", { name: /Користувачі/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /Керування шаблонами/ })).not.toBeInTheDocument();
});

it("[module1] opens administrative pages for the admin role", async () => {
  openPage("/users", {
    "GET /api/auth/me/": () => Response.json(account("admin")),
    "GET /api/users/?page=1": () => Response.json(emptyPage),
    "GET /api/templates/?page_size=100": () => Response.json(emptyPage),
  });
  expect(await screen.findByRole("heading", { name: "Користувачі" })).toBeVisible();
  expect(screen.getByText("Адміністратор", { selector: "small" })).toBeVisible();
  await userEvent.click(screen.getByRole("link", { name: /Керування шаблонами/ }));
  expect(await screen.findByRole("heading", { name: "Керування шаблонами" })).toBeVisible();
});

it("[module2] opens the selected template, saves its fields and previews the draft", async () => {
  const template: Template = { id: 7, name: "Звіт", description: "", version: 1,
    is_active: true, schema: [{ name: "hours", label: "Години", type: "number", required: true }] };
  const title = "Практика";
  const data = { hours: 4 };
  const html = "<article><h1>Практика</h1><p>Години: 4</p></article>";
  const author = account("teacher");
  const requests = openPage("/templates", {
    "GET /api/auth/me/": () => Response.json(author),
    "GET /api/templates/?page_size=100": () => Response.json({
      ...emptyPage, count: 3, results: [
        { ...template, id: 2, name: "Заява", schema: [] }, template,
        { ...template, id: 9, name: "Застарілий бланк", is_active: false },
      ],
    }),
    "GET /api/templates/7/": () => Response.json(template),
    "GET /api/auth/csrf/": () => Response.json({ csrfToken: "test-token" }),
    "POST /api/documents/": () => Response.json({ id: 42 }, { status: 201 }),
    "GET /api/documents/42/": () => Response.json({ id: 42, title, data,
      owner: author, template_snapshot: template, version: 1, status: "draft", events: [],
      age_seconds: 0, created_at: "2026-01-01T09:00:00Z", updated_at: "2026-01-01T09:00:00Z" }),
    "GET /api/documents/42/preview/": () => Response.json({ html }),
  });
  const user = userEvent.setup();
  const cards = await screen.findAllByRole("article");
  expect(cards).toHaveLength(2);
  expect(screen.queryByText("Застарілий бланк")).not.toBeInTheDocument();
  const selected = cards.find(card => within(card).queryByRole("heading", { name: "Звіт" }));
  expect(selected).toBeDefined();
  await user.click(within(selected!).getByRole("link", { name: /Використати/ }));
  await user.type(await screen.findByRole("spinbutton", { name: /Години/ }), "4");
  await user.type(screen.getByRole("textbox", { name: /Назва документа/ }), title);
  await user.click(screen.getByRole("button", { name: "Зберегти документ" }));
  expect(await screen.findByRole("heading", { name: title })).toBeVisible();
  expect(requests).toHaveBeenCalledWith("/api/documents/", expect.objectContaining({
    method: "POST", body: JSON.stringify({ title, data, template: template.id }),
  }));
  expect(screen.getByText("Чернетка")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Попередній перегляд" }));
  const preview = await screen.findByTitle("Попередній перегляд документа");
  expect(preview).toHaveAttribute("srcdoc", html);
  expect(preview).toHaveAttribute("sandbox", "");
});
