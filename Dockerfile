# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app + built frontend
FROM python:3.12-slim
WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini ./
COPY prompts/ prompts/
COPY resumes/ resumes/

# Copy built React frontend
COPY --from=frontend-build /app/frontend/dist frontend/dist/

# Create resumes directory if needed
RUN mkdir -p resumes

EXPOSE 8000

# Use the venv Python directly (uv run can swallow env vars)
ENV PATH="/app/.venv/bin:$PATH"

# Run migrations then start the server
CMD echo "DATABASE_URL=$DATABASE_URL" && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
