import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { ApiError } from "../../../shared/api/client";
import { ErrorBox } from "../../../shared/ui";
import type { Field } from "../../../shared/types";
/** Перетворює декларативну серверну схему на Zod; Backend повторює валідацію. */
export function fieldSchema(fields: Field[]) {
  const shape: Record<string, z.ZodTypeAny> = {
    title: z
      .string()
      .trim()
      .min(1, "Вкажіть назву")
      .max(250, "Максимум 250 символів"),
  };
  for (const field of fields) {
    let schema: z.ZodTypeAny;
    if (field.type === "number") {
      let number = z.coerce.number({ invalid_type_error: "Введіть число" });
      if (field.min !== undefined)
        number = number.min(field.min, `Мінімум ${field.min}`);
      if (field.max !== undefined)
        number = number.max(field.max, `Максимум ${field.max}`);
      schema = z.preprocess(
        (v) => (v === "" ? undefined : v),
        field.required ? number : number.optional(),
      );
    } else {
      let str = z.string();
      if (field.required) str = str.trim().min(1, "Обов’язкове поле");
      if (field.max_length)
        str = str.max(
          field.max_length,
          `Максимум ${field.max_length} символів`,
        );
      schema = str;
      if (field.type === "select")
        schema = str.refine(
          (v) => (!v && !field.required) || field.choices?.includes(v),
          "Оберіть допустиме значення",
        );
      if (field.type === "date")
        schema = str.refine(
          (v) =>
            (!v && !field.required) ||
            (/^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v))),
          "Вкажіть коректну дату",
        );
    }
    shape[field.name] = schema;
  }
  return z.object(shape);
}
/** Спільна форма створення/редагування; помилка API не скидає введені значення. */
export function DocumentForm({
  fields,
  title = "",
  data = {},
  onSave,
  submitLabel = "Зберегти документ",
  onReload,
}: {
  fields: Field[];
  title?: string;
  data?: Record<string, string | number>;
  onSave: (values: {
    title: string;
    data: Record<string, string | number>;
  }) => Promise<void>;
  submitLabel?: string;
  onReload?: () => Promise<void>;
}) {
  const [error, setError] = useState<unknown>();
  const {
    register,
    handleSubmit,
    setError: setFieldError,
    formState: { errors, isSubmitting },
  } = useForm<Record<string, unknown>>({
    resolver: zodResolver(fieldSchema(fields)),
    defaultValues: {
      title,
      ...Object.fromEntries(fields.map((f) => [f.name, data[f.name] ?? ""])),
    },
  });
  async function save(values: Record<string, unknown>) {
    setError(undefined);
    try {
      const { title, ...data } = values;
      await onSave({
        title: String(title),
        data: Object.fromEntries(
          Object.entries(data).filter(([, v]) => v !== undefined),
        ) as Record<string, string | number>,
      });
    } catch (e) {
      // Зокрема після 409 залишаємо введення; заміна серверними даними — явна дія.
      setError(e);
      if (e instanceof ApiError && e.body && typeof e.body === "object") {
        // DRF повертає динамічні поля у вкладеному data, а title — окремо.
        for (const [key, value] of Object.entries(e.body)) {
          if (key === "data" && value && typeof value === "object") {
            for (const [field, message] of Object.entries(value))
              setFieldError(field, { message: String(message) });
          } else if (key === "title")
            setFieldError("title", { message: String(value) });
        }
      }
    }
  }
  return (
    <form onSubmit={handleSubmit(save)} className="form-stack" noValidate>
      <ErrorBox error={error} />
      {error instanceof ApiError && error.status === 409 && onReload && (
        <div className="notice">
          Введені зміни збережено у формі. Скопіюйте їх перед завантаженням
          актуальної версії: ця дія замінить поля серверними даними.
          <button
            type="button"
            disabled={isSubmitting}
            onClick={async () => {
              try {
                await onReload();
              } catch (e) {
                setError(e);
              }
            }}
          >
            Завантажити актуальну версію
          </button>
        </div>
      )}
      <label>
        Назва документа <span aria-hidden="true">*</span>
        <input {...register("title")} aria-invalid={!!errors.title} />
        {errors.title && (
          <small className="field-error">{String(errors.title.message)}</small>
        )}
      </label>
      {fields.map((field) => (
        <label key={field.name}>
          {field.label}
          {field.required && <span aria-hidden="true"> *</span>}
          {field.type === "textarea" ? (
            <textarea
              rows={5}
              {...register(field.name)}
              aria-invalid={!!errors[field.name]}
            />
          ) : field.type === "select" ? (
            <select
              {...register(field.name)}
              aria-invalid={!!errors[field.name]}
            >
              <option value="">Оберіть значення</option>
              {field.choices?.map((choice) => (
                <option key={choice}>{choice}</option>
              ))}
            </select>
          ) : (
            <input
              type={
                field.type === "number"
                  ? "number"
                  : field.type === "date"
                    ? "date"
                    : "text"
              }
              step={field.type === "number" ? "any" : undefined}
              {...register(field.name)}
              aria-invalid={!!errors[field.name]}
            />
          )}{" "}
          {errors[field.name] && (
            <small className="field-error">
              {String(errors[field.name]?.message)}
            </small>
          )}
        </label>
      ))}
      <p className="muted small">
        * Обов’язкові поля. Збереження не надсилає документ на погодження.
      </p>
      <button className="primary" disabled={isSubmitting}>
        {isSubmitting ? "Збереження…" : submitLabel}
      </button>
    </form>
  );
}
