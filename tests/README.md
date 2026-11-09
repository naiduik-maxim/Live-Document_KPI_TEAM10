# Тести за функціональними модулями

Кожен із 35 серверних та 16 клієнтських тестів має один основний модуль. У Python шукайте декоратор `@tag("module1")` над класом або методом. У React шукайте `[module1]` у назві тесту чи групи. Для інших модулів замініть цифру. Наскрізні сценарії Playwright запускаються окремо.

| Модуль | Сервер | Інтерфейс | Усього | Команда з кореня проєкту |
|---|---:|---:|---:|---|
| 1. Авторизація, ролі та навігація | 9 | 5 | 14 | `python tests/run_module.py 1` |
| 2. Шаблони, форми та створення документа | 9 | 6 | 15 | `python tests/run_module.py 2` |
| 3. Життєвий цикл, статуси та Timeline | 11 | 4 | 15 | `python tests/run_module.py 3` |
| 4. Dashboard та експорт у Word | 6 | 1 | 7 | `python tests/run_module.py 4` |

Для запуску потрібні активне Python-середовище із залежностями з `backend/requirements-dev.txt`, Node.js та встановлені через `npm ci` залежності в `frontend/`. Скрипт запускає обидві частини й повертає код помилки, якщо будь-яка з них не пройшла. За замовчуванням Django використовує тестову SQLite. Щоб виконати дві перевірки конкурентного запису з модуля 3, задайте `USE_SQLITE=0` та налаштування тестового PostgreSQL.

## 1. Авторизація, ролі та навігація

- Сервер: успішний і відхилений вхід у [LoginTests](../backend/core/tests/test_document_modules.py), роль суперкористувача у [BusinessLogicTests](../backend/core/tests/test_business_logic.py), сесії, CSRF, доступ до документів, адміністрування шаблонів і фільтрація реєстру у [тестах API](backend/test_acceptance.py).
- Інтерфейс: очищення кешу попереднього облікового запису в [App](../frontend/src/app/App.test.tsx), вхід із поверненням до реєстру, перехід в архів та доступ до адміністративних сторінок у [Workspace](../frontend/src/app/Workspace.test.tsx).

## 2. Шаблони, форми та створення документа

- Сервер: перевірка обраної схеми у [TemplateValidationTests](../backend/core/tests/test_document_modules.py), збереження знімка шаблону й валідація у [BusinessLogicTests](../backend/core/tests/test_business_logic.py), схема, дані й попередній перегляд у [тестах API](backend/test_acceptance.py).
- Інтерфейс: вибір активного шаблону, збереження та перегляд чернетки у [Workspace](../frontend/src/app/Workspace.test.tsx), обов’язкові поля, межі значень, помилки й надсилання у [DocumentForm](../frontend/src/features/documents/components/DocumentForm.test.tsx).

## 3. Життєвий цикл, статуси та Timeline

- Сервер: зупинка годинника у [DocumentAgeTests](../backend/core/tests/test_document_modules.py), переходи, права, історія та версії у [BusinessLogicTests](../backend/core/tests/test_business_logic.py) і [LifecycleTests](backend/test_acceptance.py). Дві PostgreSQL-перевірки охоплюють конкурентний запис [через сервіс](../backend/core/tests/test_concurrency.py) і [через API](backend/test_postgres_concurrency.py).
- Інтерфейс: доступність дій для викладача та керівника у [LifecycleDashboard](../frontend/src/features/documents/pages/LifecycleDashboard.test.tsx), конфлікти версій і повторне надсилання у [DocumentDetail](../frontend/src/features/documents/pages/DocumentDetail.test.tsx).

## 4. Dashboard та експорт у Word

- Сервер: статистика після зміни статусу й повторне відкриття DOCX із перевіркою форматування у [DashboardLifecycleTests та ExportTests](../backend/core/tests/test_document_modules.py), сумісність тексту зі старих записів у [BusinessLogicTests](../backend/core/tests/test_business_logic.py), період аналітики, права видимості та вміст завантаження у [тестах API](backend/test_acceptance.py).
- Інтерфейс: один сценарій відкриває Dashboard, завершує документ, перевіряє Timeline й посилання на Word, повертається на Dashboard та звіряє нові числа і графік. Його зараховано до модуля 4 за кінцевою перевіркою. [LifecycleDashboard](../frontend/src/features/documents/pages/LifecycleDashboard.test.tsx)
