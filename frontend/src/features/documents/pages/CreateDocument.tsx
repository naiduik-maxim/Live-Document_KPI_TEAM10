import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../../shared/api/client";
import { ErrorBox, Heading, Loading } from "../../../shared/ui";
import type { Document, Template } from "../../../shared/types";
import { DocumentForm } from "../components/DocumentForm";

/** Створює документ за актуальною схемою обраного шаблону. */
export function CreateDocument() {
  const { id } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const template = useQuery({
    queryKey: ["template", id],
    queryFn: () => api<Template>(`templates/${id}/`),
  });
  return (
    <>
      <Heading title="Новий документ" description={template.data?.name} />
      <ErrorBox error={template.error} />
      {template.isLoading ? (
        <Loading />
      ) : (
        template.data && (
          <section className="panel form-panel">
            <p className="notice">
              Демонстраційний бланк · версія {template.data.version}
            </p>
            <p className="muted small">
              Реквізити виконавця заповняться з вашого профілю під час створення.
              Ім’я керівника з’явиться після затвердження.
            </p>
            <DocumentForm
              fields={template.data.schema}
              onSave={async (values) => {
                const doc = await api<Document>("documents/", "POST", {
                  ...values,
                  template: Number(id),
                });
                // Prefix invalidation охоплює всі комбінації фільтрів реєстру.
                await client.invalidateQueries({ queryKey: ["documents"] });
                await client.invalidateQueries({ queryKey: ["analytics"] });
                navigate(`/documents/${doc.id}`);
              }}
            />
          </section>
        )
      )}
    </>
  );
}
