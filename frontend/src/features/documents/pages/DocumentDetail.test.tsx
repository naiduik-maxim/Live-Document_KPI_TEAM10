import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { DocumentDetail } from "./DocumentDetail";
import { api, ApiError } from "../../../shared/api/client";
import type { Document, User } from "../../../shared/types";

vi.mock("../../../shared/api/client", async (original) => ({
  ...(await original<typeof import("../../../shared/api/client")>()),
  api: vi.fn(),
}));
vi.mock("../../auth/context/SessionContext", () => ({ useUser: () => ({ id: 1, role: "teacher" }) }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Document edit concurrency", () => {
  it("keeps unsaved input and original version across cache refresh and 409 until explicit reload", async () => {
    const original: Document = {
      id: 1,
      title: "Original",
      owner: { id: 1 } as User,
      template: 1,
      template_snapshot: {
        name: "Example", description: "", version: 1, schema: [],
      },
      data: {},
      status: "draft",
      version: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      completed_at: null,
      age_seconds: 1,
      events: [],
    };
    let latest = original;
    vi.mocked(api).mockImplementation(async (_path, method) => {
      if (method === "PATCH") throw new ApiError(409, {});
      return latest as never;
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/documents/1"]}>
          <Routes>
            <Route path="/documents/:id" element={<DocumentDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Редагувати" }),
    );
    const title = screen.getByLabelText(/Назва документа/);
    await userEvent.clear(title);
    await userEvent.type(title, "Unsaved work");
    latest = { ...original, title: "Changed remotely", version: 2 };
    client.setQueryData(["document", "1"], latest);
    expect(title).toHaveValue("Unsaved work");
    await userEvent.click(
      screen.getByRole("button", { name: "Зберегти документ" }),
    );
    await screen.findByRole("button", { name: "Завантажити актуальну версію" });
    expect(api).toHaveBeenCalledWith("documents/1/", "PATCH", {
      title: "Unsaved work", data: {}, version: 1,
    });
    expect(title).toHaveValue("Unsaved work");
    await userEvent.click(
      screen.getByRole("button", { name: "Завантажити актуальну версію" }),
    );
    await waitFor(() =>
      expect(screen.getByLabelText(/Назва документа/)).toHaveValue("Changed remotely"),
    );
  });

  it("blocks resubmission during save and refresh, then uses the saved server version", async () => {
    const original: Document = {
      id: 1,
      title: "Returned document",
      owner: { id: 1 } as User,
      template: 1,
      template_snapshot: { name: "Example", description: "", version: 1, schema: [] },
      data: {},
      status: "returned",
      version: 3,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      completed_at: null,
      age_seconds: 1,
      events: [],
    };
    const saved = { ...original, title: "Corrected document", version: 4 };
    const submitted: Document = { ...saved, status: "submitted", version: 5 };
    let resolvePatch!: (document: Document) => void;
    let resolveRefresh!: (document: Document) => void;
    const patchResponse = new Promise<Document>((resolve) => { resolvePatch = resolve; });
    const refreshResponse = new Promise<Document>((resolve) => { resolveRefresh = resolve; });
    let reads = 0;
    let transitioned = false;
    vi.mocked(api).mockImplementation(async (_path, method) => {
      if (method === "PATCH") return patchResponse as never;
      if (method === "POST") {
        transitioned = true;
        return submitted as never;
      }
      if (transitioned) return submitted as never;
      reads += 1;
      return (reads === 1 ? original : refreshResponse) as never;
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/documents/1"]}>
          <Routes><Route path="/documents/:id" element={<DocumentDetail />} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Редагувати" }));
    const title = screen.getByLabelText(/Назва документа/);
    await userEvent.clear(title);
    await userEvent.type(title, "Corrected document");
    await userEvent.click(screen.getByRole("button", { name: "Зберегти документ" }));
    const submit = screen.getByRole("button", { name: "Надіслати на погодження" });
    expect(submit).toBeDisabled();
    expect(screen.getByRole("button", { name: "Скасувати редагування" })).toBeDisabled();
    await act(async () => { resolvePatch(saved); });
    await waitFor(() => expect(reads).toBe(2));
    expect(submit).toBeDisabled();
    expect(title).toHaveValue("Corrected document");
    await act(async () => { resolveRefresh(saved); });
    await waitFor(() => expect(submit).toBeEnabled());
    await userEvent.click(submit);
    await waitFor(() => expect(api).toHaveBeenCalledWith("documents/1/transition/", "POST", {
      action: "submit", version: 4, comment: "",
    }));
    await waitFor(() => expect(client.getQueryData(["document", "1"])).toMatchObject({
      status: "submitted", version: 5,
    }));
  });
});
