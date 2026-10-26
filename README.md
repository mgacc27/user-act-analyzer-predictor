# user-act-analyzer-predictor
ПО для анализа и прогнозирования пользовательской активности, производственная практика (преддипломная практика).

## Технологический стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, pandas, PyTest 9.1.1
- **Frontend:** React.js 19.3.0, Recharts, Vite
- **Database:** PostgreSQL 18.6
- **Infrastructure:** Docker, Docker Compose, Nginx, JWT/OAuth2, bcrypt

## Быстрый старт

### Требования

- Docker Desktop
- Docker Compose v2+

### Установка и запуск

```bash
# 1. Клонировать репозиторий
git clone https://github.com/mgacc27/user-act-analyzer-predictor.git
cd user-act-analyzer-predictor

# 2. Собрать и запустить все контейнеры
docker compose up -d --build
```
### Проверка статуса

```bash
docker compose ps
```

Все три контейнера (`postgres`, `backend`, `frontend`) должны быть в состоянии **Up**.

## Доступ к системе

| Сервис | URL | Описание |
|---|---|---|
| Веб-интерфейс (Dashboard) | http://localhost | Аналитическая панель |
| Swagger UI (API) | http://localhost:8000/docs | Интерактивная документация OpenAPI |

### Учётные записи

| Роль | Логин | Пароль |
|---|---|---|
| Аналитик | `analyst` | `analyst` |
| Администратор | `admin` | `admin` |

## Генерация тестовых данных

```bash
python gen_logs.py
```

## Запуск тестов

```bash
docker compose exec backend pytest
```

## Остановка и очистка

```bash
# Остановить контейнеры (данные сохраняются)
docker compose down

# Полная очистка (включая том PostgreSQL)
docker compose down -v
```
