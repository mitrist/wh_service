# Деплой `wh_service` на VM в Яндекс Облаке

Пошаговая инструкция для прод-развертывания Django-проекта:
- Django + Gunicorn
- Nginx
- PostgreSQL
- Redis + Celery
- HTTPS через Let's Encrypt

---

## 1) Подготовка VM

1. Создайте VM (Ubuntu 22.04 LTS), минимум 2 vCPU / 4 GB RAM.
2. Откройте порты в Security Group:
   - `22/tcp` (SSH)
   - `80/tcp` (HTTP)
   - `443/tcp` (HTTPS)
3. Подключитесь по SSH:

```bash
ssh -i ~/.ssh/<KEY_NAME> <user>@<vm_public_ip>
```

---

## 2) Установка системных пакетов

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  git curl wget unzip \
  python3 python3-venv python3-pip \
  build-essential libpq-dev \
  nginx redis-server postgresql postgresql-contrib \
  fonts-dejavu-core
```

Пакет `fonts-dejavu-core` нужен для PDF-отчёта: без TTF с кириллицей ReportLab подставляет Helvetica, и русский текст в файле превращается в «квадратики».

Проверка и автозапуск:

```bash
sudo systemctl enable redis-server postgresql nginx
sudo systemctl start redis-server postgresql nginx
sudo systemctl status redis-server --no-pager
sudo systemctl status postgresql --no-pager
```

---

## 3) Клонирование проекта

```bash
cd /opt
sudo git clone git@github.com:mitrist/wh_service.git
sudo chown -R $USER:$USER /opt/wh_service
cd /opt/wh_service
```

---

## 4) Python venv и зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install gunicorn
```

---

## 5) PostgreSQL: база и пользователь

```bash
sudo -u postgres psql
```

Внутри `psql`:

```sql
CREATE DATABASE wh_service;
CREATE USER wh_user WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE wh_service TO wh_user;
\q
```

---

## 6) Переменные окружения (`.env`)

Создайте файл `/opt/wh_service/.env`:

```env
SECRET_KEY=CHANGE_ME_LONG_RANDOM_SECRET
DEBUG=False
ALLOWED_HOSTS=your-domain.ru,<vm_public_ip>

DATABASE_URL=postgres://wh_user:CHANGE_ME_STRONG_PASSWORD@127.0.0.1:5432/wh_service

CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
CELERY_TASK_ALWAYS_EAGER=False

FRONTEND_URL=https://your-domain.ru
API_ANON_THROTTLE=120/minute

# Заявки «Заказать полный аудит»: получатели писем (через запятую). Пусто — заявки только в админке.
FULL_AUDIT_NOTIFY_EMAILS=you@yourcompany.ru
DEFAULT_FROM_EMAIL=noreply@your-domain.ru
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.example
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=smtp_login
EMAIL_HOST_PASSWORD=smtp_password
```

Права на файл:

```bash
chmod 600 /opt/wh_service/.env
```

---

## 7) Подготовка Django

Важно: в проекте по умолчанию `config.settings.dev`, поэтому в проде нужно явно задать:
`DJANGO_SETTINGS_MODULE=config.settings.prod`.

```bash
cd /opt/wh_service
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.prod

python manage.py migrate
# Новые релизы могут добавлять таблицы (в т.ч. WMS чек-лист) — после git pull всегда выполняйте migrate.
python manage.py collectstatic --noinput
python manage.py seed_self_audit_questions --force
python manage.py createsuperuser
```

---

## 8) Systemd: Gunicorn

Файл `/etc/systemd/system/wh-gunicorn.service`:

```ini
[Unit]
Description=wh_service Gunicorn
After=network.target

[Service]
User=<your_user>
Group=www-data
WorkingDirectory=/opt/wh_service
EnvironmentFile=/opt/wh_service/.env
Environment="DJANGO_SETTINGS_MODULE=config.settings.prod"
ExecStart=/opt/wh_service/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 9) Systemd: Celery worker

Файл `/etc/systemd/system/wh-celery.service`:

```ini
[Unit]
Description=wh_service Celery Worker
After=network.target redis-server.service
Requires=redis-server.service

[Service]
User=<your_user>
Group=www-data
WorkingDirectory=/opt/wh_service
EnvironmentFile=/opt/wh_service/.env
Environment="DJANGO_SETTINGS_MODULE=config.settings.prod"
ExecStart=/opt/wh_service/.venv/bin/celery -A config worker -l info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable wh-gunicorn wh-celery
sudo systemctl start wh-gunicorn wh-celery
sudo systemctl status wh-gunicorn --no-pager
sudo systemctl status wh-celery --no-pager
```

---

## 10) Nginx reverse proxy

Файл `/etc/nginx/sites-available/wh_service`:

```nginx
server {
    listen 80;
    server_name your-domain.ru <vm_public_ip>;

    client_max_body_size 20M;

    location /static/ {
        alias /opt/wh_service/staticfiles/;
    }

    location /media/ {
        alias /opt/wh_service/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300;
    }
}
```

Активация:

```bash
sudo ln -s /etc/nginx/sites-available/wh_service /etc/nginx/sites-enabled/wh_service
sudo nginx -t
sudo systemctl restart nginx
```

---

## 11) HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.ru
sudo certbot renew --dry-run
```

---

## 12) Проверка

Проверьте в браузере:
- `https://your-domain.ru/`
- `https://your-domain.ru/admin/`
- `https://your-domain.ru/api/docs/`

Функционально:
1. Пройдите квиз.
2. Дойдите до результата.
3. Скачайте PDF (это проверка Celery + Redis + ReportLab).

---

## 13) Обновление приложения из Git

Выполняйте на VM под тем же пользователем, от которого клонировали проект и который указан в `User=` в unit-файлах systemd (чтобы не ломались права на `.venv` и файлы).

### 13.1) Подключение и проверка репозитория

```bash
ssh -i ~/.ssh/<KEY_NAME> <user>@<vm_public_ip>
cd /opt/wh_service
git status
```

- Если видите незакоммиченные правки в отслеживаемых файлах, либо сохраните их (`git stash`), либо не обновляйте, пока не разберётесь — иначе `git pull` может остановиться с конфликтом.
- Файл `.env` в репозиторий не попадает (он локальный на сервере) — при обновлении он не перезаписывается.

### 13.2) Получить изменения с GitHub

Рекомендуется явно указать ветку (в проекте по умолчанию — `main`):

```bash
cd /opt/wh_service
git fetch origin
git pull origin main
```

Если появилось сообщение о конфликте слияния — разрешите конфликты вручную или откатитесь к последнему коммиту на сервере и повторите pull после исправления на стороне репозитория.

### 13.3) Зависимости Python

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 13.4) Миграции, статика, данные квиза

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py migrate
python manage.py collectstatic --noinput
```

Если в релизе менялись вопросы/ответы самоаудита (код или сиды), перезаполните вопросы:

```bash
python manage.py seed_self_audit_questions --force
```

### 13.5) Перезапуск сервисов

```bash
sudo systemctl restart wh-gunicorn wh-celery
sudo systemctl reload nginx
```

Проверка:

```bash
sudo systemctl status wh-gunicorn --no-pager
sudo systemctl status wh-celery --no-pager
```

### 13.6) Краткая шпаргалка (одним блоком)

```bash
cd /opt/wh_service
git fetch origin && git pull origin main
source .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py migrate
python manage.py collectstatic --noinput
# при необходимости: python manage.py seed_self_audit_questions --force
sudo systemctl restart wh-gunicorn wh-celery
sudo systemctl reload nginx
```

---

## 14) Диагностика

```bash
sudo journalctl -u wh-gunicorn -f
sudo journalctl -u wh-celery -f
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

Проверка Gunicorn локально:

```bash
curl -I http://127.0.0.1:8000/
```

---

## 15) Частые проблемы

### `Permission denied` в `.venv`
Исправьте владельца и пересоздайте окружение:

```bash
sudo chown -R $USER:$USER /opt/wh_service
rm -rf /opt/wh_service/.venv
python3 -m venv /opt/wh_service/.venv
```

### На странице результата ошибка `Missing required answer for qX`
Сессия не завершена полностью — нужно вернуться в квиз и ответить на пропущенный вопрос.

### В PDF вместо русского текста «квадратики»
На сервере не найден TTF с кириллицей (часто на минимальном образе Ubuntu). Установите шрифты и перезапустите Celery (PDF собирается в воркере):

```bash
sudo apt install -y fonts-dejavu-core
sudo systemctl restart wh-celery
```

В логах воркера при старте генерации PDF должна появиться строка вида `pdf_generator: using fonts /usr/share/fonts/truetype/dejavu/...`. Если видите предупреждение про Helvetica — шрифты всё ещё не подхватились.

