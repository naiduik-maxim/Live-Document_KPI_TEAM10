import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";
import { api } from "../shared/api/client";

vi.mock("../shared/api/client", () => ({ api: vi.fn() }));
vi.mock("./routes/AppRoutes", () => ({ AppRoutes: () => <h1>Workspace</h1> }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("[module1] discards the previous account's cached data on successful login", async () => {
  vi.mocked(api).mockImplementation(async (path) => {
    if (path === "auth/me/") return null as never;
    return { id: 2, username: "second", first_name: "", last_name: "", role: "teacher" } as never;
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(["document", "1"], { title: "Other account private document" });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/login"]}><App /></MemoryRouter></QueryClientProvider>);
  await userEvent.type(await screen.findByLabelText("Логін"), "second");
  await userEvent.type(screen.getByLabelText("Пароль"), "password");
  await userEvent.click(screen.getByRole("button", { name: "Увійти" }));
  await waitFor(() => expect(client.getQueryData(["me"])).toMatchObject({ id: 2 }));
  expect(client.getQueryData(["document", "1"])).toBeUndefined();
});
