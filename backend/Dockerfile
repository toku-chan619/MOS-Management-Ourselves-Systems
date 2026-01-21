FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optional: Install Ollama CLI (uncomment if using ollama_cli backend)
# RUN curl -fsSL https://ollama.ai/install.sh | sh

# Optional: Install Claude CLI (uncomment if using claude_cli backend)
# Note: Claude CLI requires authentication setup
# RUN curl -fsSL https://docs.anthropic.com/claude/docs/install-cli | sh

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
