import { useQuery } from "@tanstack/react-query";
import { api } from "../../../shared/api/client";
import type { Page, Template } from "../../../shared/types";

/** Завантажує всі сторінки каталогу для форм вибору й адміністрування. */
export function useTemplates() {
  return useQuery({
    // Каталог спільний для вибору й admin; після зміни схеми інвалідуємо цей ключ.
    queryKey: ["templates"],
    queryFn: async () => {
      let url = "templates/?page_size=100";
      const all: Template[] = [];
      // Навіть понад 100 шаблонів не мають зникати із select через серверну пагінацію.
      while (url) {
        const page = await api<Page<Template>>(url);
        all.push(...page.results);
        url = page.next
          ? `templates/${new URL(page.next, window.location.origin).search}`
          : "";
      }
      return all;
    },
  });
}
