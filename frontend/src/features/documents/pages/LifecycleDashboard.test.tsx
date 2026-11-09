import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "../../../shared/api/client";
import type { Analytics, Document, User } from "../../../shared/types";
import { AnalyticsPage } from "../../analytics/pages/AnalyticsPage";
import { SessionContext } from "../../auth/context/SessionContext";
import { DocumentDetail } from "./DocumentDetail";

vi.mock("../../../shared/api/client", async (original) => ({
  ...(await original<typeof import("../../../shared/api/client")>()),
  api: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

const owner: User = {
  id: 1, username: "author", first_name: "Автор", last_name: "",
  email: "", is_active: true, role: "teacher",
};
const manager: User = { ...owner, id: 2, first_name: "Керівник", role: "manager" };
const submitted: Document = {
  id: 7, title: "Протокол засідання", owner, template: 3,
  template_snapshot: { name: "Протокол", description: "", version: 1, schema: [] },
  data: {}, status: "submitted", version: 2,
  created_at: "2026-01-10T08:00:00Z", updated_at: "2026-01-10T09:30:00Z",
  completed_at: null, age_seconds: 5400,
  events: [{
    id: 2, from_status: "draft", to_status: "submitted", actor: owner,
    comment: "", created_at: "2026-01-10T09:30:00Z",
  }],
};

function openPage(viewer: User, path: string) {
  // Keep data fresh across navigation unless the application invalidates it.
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  render(
    <QueryClientProvider client={client}>
      <SessionContext.Provider value={viewer}>
        <MemoryRouter initialEntries={[path]}>
          <Link to="/">Dashboard</Link>
          <Link to="/documents/7">Картка</Link>
          <Routes>
            <Route path="/" element={<AnalyticsPage />} />
            <Route path="/documents/:id" element={<DocumentDetail />} />
          </Routes>
        </MemoryRouter>
      </SessionContext.Provider>
    </QueryClientProvider>,
  );
}

it.each([owner, manager])("[module3] shows review actions according to the $role role", async (viewer) => {
  vi.mocked(api).mockResolvedValue(submitted);
  openPage(viewer, "/documents/7");
  await screen.findByRole("heading", { name: submitted.title });
  expect(screen.getByRole("banner")).toHaveTextContent("На погодженні");
  const approve = screen.queryByRole("button", { name: "Затвердити" });
  const sendBack = screen.queryByRole("button", { name: "Повернути на доопрацювання" });
  if (viewer.role === "teacher") {
    expect(approve).not.toBeInTheDocument();
    expect(sendBack).not.toBeInTheDocument();
  } else {
    expect(approve).toBeEnabled();
    expect(sendBack).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Коментар погодження"), "Уточнити дату");
    expect(sendBack).toBeEnabled();
  }
});

it("[module4] completes an approved document, shows its timeline and refreshes dashboard figures", async () => {
  const approved: Document = {
    ...submitted, status: "approved", version: 3,
    events: [...submitted.events, {
      id: 3, from_status: "submitted", to_status: "approved", actor: manager,
      comment: "Погоджено без зауважень", created_at: "2026-01-10T09:35:00Z",
    }],
    updated_at: "2026-01-10T09:35:00Z", age_seconds: 5700,
  };
  const completed: Document = {
    ...approved, status: "completed", version: 4, age_seconds: 7200,
    updated_at: "2026-01-10T10:00:00Z", completed_at: "2026-01-10T10:00:00Z",
    events: [...approved.events, {
      id: 4, from_status: "approved", to_status: "completed", actor: owner,
      comment: "", created_at: "2026-01-10T10:00:00Z",
    }],
  };
  let current = approved;
  vi.mocked(api).mockImplementation(async <T,>(path: string, method?: string): Promise<T> => {
    if (path === "documents/7/transition/" && method === "POST") {
      current = completed;
      return current as T;
    }
    if (path === "documents/7/") return current as T;
    if (path === "analytics/?date_from=&date_to=") {
      const done = current.status === "completed";
      const stats: Analytics = {
        total: 4, pending_approval: 1, completed_in_period: done ? 1 : 0,
        average_cycle_seconds: done ? 7200 : null,
        by_status: { draft: 2, submitted: 1, returned: 0, approved: done ? 0 : 1, completed: done ? 1 : 0 },
        creation_trend: [{ date: "2026-01-09", count: 3 }, { date: "2026-01-10", count: 1 }],
      };
      return stats as T;
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  openPage(owner, "/");
  const stat = (label: string) => screen.getByText(label).closest("section")?.querySelector("strong");
  await screen.findByRole("img", { name: "2026-01-09: 3, 2026-01-10: 1" });
  expect(stat("Усього документів")).toHaveTextContent(/^4$/);
  expect(stat("Очікують погодження")).toHaveTextContent(/^1$/);
  expect(stat("Завершено за період")).toHaveTextContent(/^0$/);
  expect(stat("Середній цикл")).toHaveTextContent("—");

  await userEvent.click(screen.getByRole("link", { name: "Картка" }));
  expect(await screen.findByText("1 год 35 хв")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Завершити документ" }));
  expect(await screen.findByText("2 год 0 хв · зупинено")).toBeVisible();
  expect(api).toHaveBeenCalledWith("documents/7/transition/", "POST", {
    action: "complete", version: 3, comment: "",
  });
  expect(screen.getByRole("banner")).toHaveTextContent("Завершено");
  expect(screen.queryByRole("button", { name: "Завершити документ" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Редагувати" })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Word/ })).toHaveAttribute("href", "/api/documents/7/export/");
  const stages = within(screen.getByRole("list")).getAllByRole("listitem");
  expect(stages.map((item) => item.querySelector("strong")?.textContent))
    .toEqual(["На погодженні", "Затверджено", "Завершено"]);
  expect(stages[1]).toHaveTextContent("Керівник");
  expect(stages[1]).toHaveTextContent("Погоджено без зауважень");

  await userEvent.click(screen.getByRole("link", { name: "Dashboard" }));
  await screen.findByText("2 год 0 хв");
  expect(stat("Завершено за період")).toHaveTextContent(/^1$/);
  expect(stat("Середній цикл")).toHaveTextContent("2 год 0 хв");
  expect(document.querySelector(".bar.completed")).toHaveStyle({ width: "25%" });
  expect(document.querySelector(".bar.approved")).toHaveStyle({ width: "0%" });
});
