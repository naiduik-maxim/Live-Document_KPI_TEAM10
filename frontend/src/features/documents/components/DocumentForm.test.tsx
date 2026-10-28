import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach } from "vitest";
import { DocumentForm, fieldSchema } from "./DocumentForm";
import { errorMessage } from "../../../shared/api/client";
import type { Field } from "../../../shared/types";
afterEach(cleanup);
const fields: Field[] = [
  {
    name: "recipient",
    label: "Адресат",
    type: "text",
    required: true,
    max_length: 10,
  },
  {
    name: "count",
    label: "Кількість",
    type: "number",
    required: true,
    min: 1,
    max: 5,
  },
  {
    name: "kind",
    label: "Тип",
    type: "select",
    required: true,
    choices: ["Перший", "Другий"],
  },
];
describe("Dynamic document forms", () => {
  it("rejects missing, oversized, out-of-range and unknown choice values", () => {
    const schema = fieldSchema(fields);
    expect(
      schema.safeParse({ title: "", recipient: "", count: "", kind: "" })
        .success,
    ).toBe(false);
    expect(
      schema.safeParse({
        title: "Назва",
        recipient: "12345678901",
        count: 6,
        kind: "Третій",
      }).success,
    ).toBe(false);
    expect(
      schema.safeParse({
        title: "Назва",
        recipient: "Адресат",
        count: 1,
        kind: "Перший",
      }).success,
    ).toBe(true);
  });
  it("shows required field errors and never submits invalid form", async () => {
    const save = vi.fn();
    render(<DocumentForm fields={fields} onSave={save} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Зберегти документ" }),
    );
    expect(await screen.findByText("Вкажіть назву")).toBeInTheDocument();
    expect(save).not.toHaveBeenCalled();
  });
  it("preserves literal text, normalizes numeric values and submits once", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    render(<DocumentForm fields={fields} onSave={save} />);
    await userEvent.type(
      screen.getByLabelText(/Назва документа/),
      "<b>Текст</b>",
    );
    await userEvent.type(screen.getByLabelText(/Адресат/), "Іван");
    await userEvent.type(screen.getByLabelText(/Кількість/), "3");
    await userEvent.selectOptions(screen.getByLabelText(/Тип/), "Другий");
    await userEvent.click(
      screen.getByRole("button", { name: "Зберегти документ" }),
    );
    await waitFor(() => expect(save).toHaveBeenCalledTimes(1));
    expect(save).toHaveBeenCalledWith({
      title: "<b>Текст</b>",
      data: { recipient: "Іван", count: 3, kind: "Другий" },
    });
  });
  it("renders server failure and retains entered data", async () => {
    const save = vi.fn().mockRejectedValue(new Error("Не вдалося зберегти"));
    render(<DocumentForm fields={[]} title="Моя чернетка" onSave={save} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Зберегти документ" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Не вдалося зберегти",
    );
    expect(screen.getByLabelText(/Назва документа/)).toHaveValue(
      "Моя чернетка",
    );
  });
  it("explains permission, expiry, missing objects and stale writes", () => {
    expect(errorMessage(401, {})).toContain("Увійдіть");
    expect(errorMessage(403, {})).toContain("прав");
    expect(errorMessage(404, {})).toContain("не знайдено");
    expect(errorMessage(409, {})).toContain("Оновіть");
  });
});
