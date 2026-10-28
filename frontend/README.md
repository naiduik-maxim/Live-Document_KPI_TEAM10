# Frontend

React + TypeScript + Vite. Сторінки працюють із Django API `/api/` через
same-origin session cookie та CSRF. Загальна інструкція запуску — у
[`../README.md`](../README.md).

```text
src/
  app/                 # session gate, layout, routes, infrastructure providers
  features/
    auth/              # login, session query, незалежний SessionContext
    documents/         # registry/archive, create/detail pages, dynamic form
    templates/         # template library та запит повного каталогу
    analytics/         # серверні агрегати й графіки
    admin/             # керування користувачами та JSON-схемами шаблонів
  shared/
    api/client.ts      # JSON transport, CSRF та помилки DRF
    types.ts           # API DTO й локалізовані назви
    ui/                # повторно використовувані компоненти
    utils/format.ts    # Europe/Kyiv та тривалість
  main.tsx             # точка входу
  styles.css           # спільні токени/стилі, збережені без візуальних змін
```

Тести розміщено поруч із відповідними App/DocumentForm/DocumentDetail.
Залежності спрямовано `app → features → shared`; auth context не залежить від
App або сторінок. Для повторного використання компонентів достатньо прямих
імпортів; спільний `ui/index.tsx` містить невеликі UI-компоненти.

`["me"]` — поточна сесія; login/logout очищують cache. Ключі списків документів
включають URL-фільтри, деталі — id, preview — id і version, аналітика — період.
Після зміни документа інвалідуються деталі, реєстри та аналітика. Редактор
тримає snapshot значень і version до явного перезавантаження, щоб 409 або
фоновий refetch не втрачали незбережений текст. Після успішного PATCH його
відповідь одразу оновлює cache, а редактор закривається після оновлення запитів:
повторне надсилання не може використати попередню version. Динамічна Zod-схема допомагає
користувачу, але остаточну валідацію та права перевіряє Django.

```bash
npm ci
npm run dev
npm run build
npm test
```

Vite проксіює `/api/` та `/admin/` на `127.0.0.1:8000`. Для контейнерного
запуску застосовується Nginx із кореневого Docker Compose.
