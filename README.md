# JobShield

**Assess the risk of a job posting before you apply.**

JobShield helps job seekers spot signs of recruitment scams, check employer details against reviewed sources, and browse community warnings. You can analyze a posting or look up an employer without creating an account.

[Features](#features) · [Quick start](#quick-start) · [Architecture](#architecture)

## Features

| Feature | What you can do |
| --- | --- |
| Job posting analysis | Paste text, upload an image, or enter a public URL. Review any extracted text, then see the risk level, the signals that informed it, and suggested next steps. |
| Employer lookup | Compare company and contact details with reviewed sources. See the evidence and any gaps for each field. |
| Optional AI explanations | Choose whether to send the posting to an AI provider for an explanation. The rules engine determines the risk level. |
| Community reports | Sign in to submit a report with evidence and track its status. Published warnings go through moderation and have personal information removed. |
| Saved analyses | Sign in to save analyses and revisit them later. |

> Use the results to guide your own checks. Contact the employer through an official channel before sending money or sharing identity documents.

## Quick start

Install Git, [uv](https://docs.astral.sh/uv/), Node.js 24.8 or later within the 24.x series, npm 11, and PostgreSQL. To extract text from images, install Tesseract with the Vietnamese (`vie`) and English (`eng`) language packs.

1. **Clone the repository and copy the configuration templates.** Create a dedicated PostgreSQL database for development and set `DATABASE_URL` in `backend/.env` to its connection string.

   ```sh
   git clone https://github.com/Sntug/JobShield.git
   cd JobShield
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```

2. **Start the API.** Run these commands from the repository root.

   ```sh
   cd backend
   uv python install
   uv sync --frozen
   uv run alembic upgrade head
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. **Start the frontend.** Open a second terminal at the repository root.

   ```sh
   cd frontend
   npm ci --include=optional
   npm run dev
   ```

4. **Analyze a sample posting.** Open the [analysis page](http://localhost:3000/analyze) and paste a sample job posting. You can also open [employer lookup](http://localhost:3000/verify-employer), browse [community warnings](http://localhost:3000/safety), or explore the [interactive API docs](http://127.0.0.1:8000/docs).

A fresh database has no employer sources. To populate it for local development, follow the [source import guide](backend/data/README.md#kiểm-tra-và-nhập-nguồn). To enable optional Gemini explanations, set `AI_PROVIDER=gemini` and `AI_API_KEY` in `backend/.env`. Keep secrets in the backend configuration.

## Architecture

| Component | Role |
| --- | --- |
| [Frontend](frontend/) | Next.js App Router, React, TypeScript, and Tailwind CSS power the guest, account, and admin interfaces. |
| [Backend](backend/) | FastAPI and Pydantic power the `/api/v1` endpoints for extraction, risk scoring, employer lookup, and reporting. Tesseract extracts text from images. |
| [Database migrations](backend/alembic/) | Alembic manages the PostgreSQL schema. The backend accesses the database through SQLAlchemy. |
