# Живі документи кафедри ІПЗЕ

Локальна вебсистема на Django REST Framework, PostgreSQL і React/TypeScript: динамічні бланки, реєстр, погодження, історія, аналітика та справжній DOCX. Вхід через облікові записи Django. П'ять вбудованих шаблонів — **демонстраційні приклади, не офіційні документи кафедри**.

## Швидкий запуск у Docker (Windows та Linux)

Потрібен Docker Desktop із Linux containers (Windows) або Docker Engine із Compose 2.24.4+ (Linux). Команди виконуються з кореня проєкту.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
# Відредагуйте .env: установіть власні POSTGRES_PASSWORD та DJANGO_SECRET_KEY.
docker compose config --quiet
docker compose up --build -d
docker compose exec backend python manage.py createsuperuser
docker compose ps
```

Linux:

```bash
cp .env.example .env
# Відредагуйте .env: установіть власні POSTGRES_PASSWORD та DJANGO_SECRET_KEY.
docker compose config --quiet
docker compose up --build -d
docker compose exec backend python manage.py createsuperuser
docker compose ps
```

Відкрити [систему](http://localhost:8080), [Django Admin](http://localhost:8080/admin/), [Swagger](http://localhost:8080/api/docs/) та [OpenAPI](http://localhost:8080/api/schema/). Міграції та ідемпотентна команда `seed_templates` виконуються автоматично перед сервером. Створений superuser має адміністративні права; інших користувачів створюйте на сторінці «Користувачі» або в Django Admin, обираючи teacher, manager чи admin. Паролі не постачаються в репозиторії.

База зберігається у volume `postgres_data`; `docker compose restart` і `docker compose down` не видаляють дані. **Не використовуйте `down -v`, якщо дані потрібні.** Порт прив'язаний лише до localhost. Для зупинки: `docker compose down`.

## Локальна розробка

Потрібні Python 3.12+, Node.js 22.12+ із npm і PostgreSQL 16. Створіть порожню БД та користувача PostgreSQL із правами на цю БД (для тестів — також CREATEDB). Скопіюйте `.env.example` у `.env`, задайте власні секрети та додайте:

```dotenv
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
DJANGO_DEBUG=1
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Backend, Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.lock.txt
cd backend
python manage.py migrate
python manage.py seed_templates
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Backend, Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.lock.txt
cd backend
python manage.py migrate
python manage.py seed_templates
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Frontend, в іншому терміналі, обидві ОС:

```text
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Відкрийте [локальний інтерфейс](http://127.0.0.1:5173). Vite проксіює API до Django, тому cookies і CSRF працюють з одного origin. Не змішуйте localhost і 127.0.0.1 в одній сесії.

Якщо PostgreSQL недоступний, **лише для локальної розробки** можна встановити `USE_SQLITE=1` у `.env`. SQLite не замінює перевірок блокування рядків і конкурентних транзакцій у PostgreSQL. Docker завжди використовує PostgreSQL.

## Перевірки

З активованим Python venv, каталог `backend/`:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Frontend:

```text
cd frontend
npm ci
npm test -- --run
npm run build
```

Незалежні API та Playwright сценарії, точні команди й **фактичні**, а не очікувані результати наведені у [звіті QA](docs/test-report.md). Для PostgreSQL тести виконуються з тими ж змінними середовища, що й застосунок; користувач БД має мати право створення тестової бази.

Повний ізольований тестовий стек, із кореня репозиторію (однакові Docker-команди для Windows/Linux):

```text
docker compose -p living-documents-test -f compose.yaml -f compose.test.yaml up --build -d --wait
docker compose -p living-documents-test -f compose.yaml -f compose.test.yaml exec -T backend python manage.py check
docker compose -p living-documents-test -f compose.yaml -f compose.test.yaml exec -T backend python manage.py makemigrations --check --dry-run
docker compose -p living-documents-test -f compose.yaml -f compose.test.yaml exec -T -e PYTHONPATH=/ backend python manage.py test core tests.backend
docker compose -p living-documents-test -f compose.yaml -f compose.test.yaml exec -T -e PYTHONPATH=/app -e E2E_TEST_DATABASE=living_documents_e2e backend python /tests/e2e/bootstrap.py
cd tests/e2e
npm ci
npx playwright install chromium
```

Після цього Windows PowerShell:

```powershell
$env:E2E_BASE_URL = 'http://127.0.0.1:8081'
npm test
```

Або Linux:

```bash
E2E_BASE_URL=http://127.0.0.1:8081 npm test
```

Синтетичні E2E-користувачі створюються **лише в тестовій БД** `living_documents_e2e`. Основна база на порту 8080 не використовує тестові паролі. Конфігурація CI повторює ці перевірки. Зупинка тестового стека з кореня: `docker compose -p living-documents-test -f compose.yaml -f compose.test.yaml down`.

Вимірювання покриття Backend у тестовому контейнері, з кореня (до його перезапуску/перестворення):

```text
docker compose -p living-documents-test -f compose.yaml -f compose.test.yaml exec -T backend python -m pip install --target /tmp/test-tools coverage==7.13.1
docker compose -p living-documents-test -f compose.yaml -f compose.test.yaml exec -T -e PYTHONPATH=/:/tmp/test-tools backend sh -c "python -m coverage run manage.py test core tests.backend --noinput && python -m coverage report"
```

Після додавання коментарів і структурування Frontend (20.10.2026): PostgreSQL **29/29**, React **8/8**, Playwright desktop/mobile **6/6**, браузерні DOCX **2/2**. TypeScript, production build, Black, isort і pycodestyle пройшли. Виправлено використання застарілої версії при повторному надсиланні одразу після збереження. Покриття statements модуля `core` до рефакторингу — **96%**; повторно його не вимірювали. Фактичні журнали, точні команди та використаний локальний CSRF override — у [звіті рефакторингу](docs/refactor-test-report.md). Поточні сторонні ngrok origins у `compose.test.yaml` потребують цього override для наведених вище команд тестового стека.

## Структура та рішення

```text
backend/              Django, DRF, міграції, сервіси, DOCX, unit tests
frontend/             React, маршрути, форми, API client, component tests
tests/                незалежні API та Playwright E2E тести
docs/                 архітектура, API, вимоги й результати перевірок
compose.yaml          PostgreSQL + Django + Nginx/React
.env.example          лише приклади, без справжніх секретів
```


