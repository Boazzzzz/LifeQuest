# LifeQuest Runtime

This guide describes the lightweight Windows runtime setup for keeping the LifeQuest backend available at `http://127.0.0.1:8000`.

The daily runtime uses `uvicorn app.main:app` without `--reload`. Use `--reload` only while actively developing.

## Prerequisites

From the repository root:

```powershell
python -m venv .venv
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Fill `.env` only for the integrations you want to use. The default SQLite database path is `data/lifequest.db`.

## Manual Runtime Commands

Start the backend:

```powershell
.\scripts\runtime\start-lifequest.ps1
```

Check status:

```powershell
.\scripts\runtime\status-lifequest.ps1
```

Open the dashboard:

```powershell
.\scripts\runtime\open-dashboard.ps1
```

Stop the backend:

```powershell
.\scripts\runtime\stop-lifequest.ps1
```

Logs are written to `data\logs\lifequest-server-YYYY-MM-DD.log`.

## Windows Login Startup

Register a user-level Windows Task Scheduler task:

```powershell
.\scripts\runtime\register-lifequest-startup-task.ps1
```

The task name is `LifeQuest Backend`. It runs when you log in and starts the backend in the background.

Remove the startup task:

```powershell
.\scripts\runtime\unregister-lifequest-startup-task.ps1
```

Check whether the task exists:

```powershell
Get-ScheduledTask -TaskName "LifeQuest Backend"
```

## Runtime Boundaries

- The backend binds to `127.0.0.1:8000` by default, so it is local-only.
- The scripts do not open the browser automatically.
- The startup task only starts the web backend. Scheduled Anki, Notion, or GitHub jobs remain separate.
- If port `8000` is already in use and `/health` is not healthy, the start script stops and asks you to inspect the status.
