# Todo App with AuthTuna

A comprehensive todo application demonstrating two implementation approaches: a simple server-rendered app and an advanced full-stack app, both integrated with AuthTuna for authentication and authorization.

Tbh most of the code in this is just plain ai gen. But it does show how to use org in a manner. 

Well I prompted and made the advanced one just to show that its possible to use **mongodb** and **nextjs** with **authtuna**.

My usual stack is **FastAPI + NextJS + MongoDB + Authtuna** as its ez to make better ui using next.

You can check out:

- [Storm Timeline](https://timeline.shashstorm.in) This uses Authtuna for RBAC and AUTH. This dosent implement orgs but gives feel like making a team and giving role in it.
- [Storm Weaver](https://weaver.shashstorm.in) A collaborative blogging platform with orgs teams etc, This uses authtuna only for AUTH as migrating the rbac system from my old logic was a bit too much work for now.
- I even have a custom vps dashboard which uses authtuna (it currently works perfectly file but if i want to make it public i will need to test for exploits and make it more configurable etc etc so no plans on making it public rn.)

## Overview

This project shows two ways to build a todo app with AuthTuna:
- Simple: one FastAPI service with Jinja templates (SSR)
- Advanced: FastAPI API + Next.js frontend (SPA)

Both use AuthTuna for signup/login, sessions, orgs, and permissions.

---

## Simple (folder: `simple/`)

What it is (short):
- FastAPI app with Jinja2 server-rendered pages
- Single service; no Node.js required
- Uses AuthTuna routes mounted at `/auth/*`
- Stores todos in the same SQL DB (via SQLAlchemy Base from AuthTuna)
- Runs on http://localhost:5080

Key routes implemented by this app:
- `GET /` → redirects to `/todos` if logged in, else to `/auth/login?return_url=/`
- `GET /todos` → list current user's todos (SSR)
- `POST /todos/add` → add a todo (form POST)
- `GET /todos/{id}/delete` → delete a todo

AuthTuna routes used:
- `GET /auth/login?return_url=/` → Login/Sign up UI (provided by AuthTuna)

How to run (Windows PowerShell):
```
# from repo root
cd simple
python main.py
```
Then open:
- App (redirects to AuthTuna login): http://localhost:5080/
- After login, todos page: http://localhost:5080/todos
- Direct login link: http://localhost:5080/auth/login?return_url=/

---

## Advanced (folder: `advanced/`)

TBH a lot more can be done to improve feel, experience, like using the org routes to fetch and show as dropdown etc etc, instead of using the included orgs page and manual copy paste. (Just me being lazy to make it, may do at a later date.)

What it is (short):
- FastAPI backend (MongoDB) exposing a JSON API
- Next.js (TypeScript, Tailwind) frontend consuming the API
- Dark mode-only UI (no light theme)
- AuthTuna for sessions, orgs, admin UI, and MFA flows

Backend (FastAPI):
- Port: http://localhost:5080
- CORS: allows localhost origins
- AuthTuna API mounted at `/auth/*`, admin UI at `/admin/*`
- Todos API:
  - `GET /api/todos` → list current user's org-scoped todos
  - `POST /api/todos` → create todo (body: `{ content, org_id }`)
  - `DELETE /api/todos/{todo_id}` → delete todo
- Admin cleanup task:
  - `POST /api/admin/run-cleanup-step` (Admin only)

Frontend (Next.js):
- Port (dev): http://localhost:3000
- Pages:
  - `/login` → username/email + password login (POST `/auth/login`)
  - `/signup` → username, email, password signup (POST `/auth/signup`)
  - `/` → landing + todo list (uses `/api/todos`, add/delete)
- API base URL configured at `advanced/todo_frontend/lib/api.ts`: `http://localhost:5080`

How to run (Windows PowerShell):
```
# 1) Start the backend (terminal 1)
cd advanced
python main.py

# 2) Start the frontend (terminal 2)
cd advanced\todo_frontend
npm install
npm run dev
```
Open:
- Frontend app: http://localhost:3000
- Backend root: http://localhost:5080
- Auth login: http://localhost:5080/auth/login
- Auth signup: http://localhost:5080/auth/signup
- Organizations UI: http://localhost:5080/ui/organizations
- Admin dashboard: http://localhost:5080/admin/dashboard
- API docs (OpenAPI): http://localhost:5080/docs

Notes:
- Frontend includes cookies with requests (configured in `api.ts`). Keep both apps on localhost for same-site cookies to work smoothly.
- The landing page expects you to belong to an organization and uses the provided Org ID when adding todos.

---

## Prerequisites

- Python 3.9+
- Node.js 22+ (only for the advanced Next.js frontend)
- MongoDB running locally (only for the advanced backend)

Install Python deps (from repo root):
```
pip install -r requirements.txt
```

In This repo I have included the basic env vars, you can play around with the vars and try.

```
# AuthTuna
AUTHTUNA_SECRET_KEY=your-secret-key-here
AUTHTUNA_DATABASE_URL=sqlite:///./authtuna.db

# Advanced backend
MONGODB_URL=mongodb://localhost:27017/todo_app
```

---

## Quick Links

Backend (advanced):
- http://localhost:5080
- http://localhost:5080/auth/login
- http://localhost:5080/auth/signup
- http://localhost:5080/ui/organizations
- http://localhost:5080/admin/dashboard
- http://localhost:5080/docs

Frontend (advanced):
- http://localhost:3000
- http://localhost:3000/login
- http://localhost:3000/signup

Simple (SSR):
- http://localhost:5080/
- http://localhost:5080/todos

---

## Tech Summary

- Simple: FastAPI + Jinja2 + SQLAlchemy (AuthTuna Base) + AuthTuna auth
- Advanced: FastAPI + MongoDB + AuthTuna + Next.js + TypeScript + Tailwind

If anything differs in your environment (ports/DB), update:
- Backend: `advanced/main.py` (port 5080)
- Frontend API base: `advanced/todo_frontend/lib/api.ts`
