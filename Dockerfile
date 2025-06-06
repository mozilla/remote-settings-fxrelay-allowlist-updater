FROM python:3.12-slim

# Set environment variables to prevent Python from writing pyc files and to avoid buffering in logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install Poetry
RUN pip install --no-cache-dir poetry

# Add a non-privileged user for running the application
RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

# Set the working directory in the container
WORKDIR /app

# Copy the project files
COPY pyproject.toml poetry.lock* /app/

# Install dependencies without creating a virtual environment (use the system Python environment)
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# Copy the rest of the application files
COPY . /app

# Command to run your application (replace `your_script.py` with the main entry point)
CMD ["python", "script.py"]
