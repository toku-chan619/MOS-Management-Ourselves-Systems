# LLM Providers

MOS supports multiple LLM backends for flexibility in deployment and cost optimization.

## Supported Backends

### 1. OpenAI API (Default)

**Backend**: `openai_api`

Uses OpenAI's API for LLM calls. Recommended for production use.

**Configuration:**
```env
LLM_BACKEND=openai_api
OPENAI_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-4o-mini
```

**Pros:**
- High quality responses
- Reliable and fast
- JSON mode support
- Well-documented

**Cons:**
- Requires API key
- Usage costs
- Requires internet connection

---

### 2. Claude CLI

**Backend**: `claude_cli`

Uses Anthropic's Claude CLI for LLM calls. Useful for authenticated CLI environments.

**Setup:**

1. Install Claude CLI:
   ```bash
   curl -fsSL https://docs.anthropic.com/claude/docs/install-cli | sh
   ```

2. Authenticate:
   ```bash
   claude auth login
   ```

3. Configure:
   ```env
   LLM_BACKEND=claude_cli
   CLAUDE_CLI_PATH=claude
   # OPENAI_API_KEY is not required
   ```

**Docker Setup:**

Uncomment the Claude CLI installation in `Dockerfile`:
```dockerfile
RUN curl -fsSL https://docs.anthropic.com/claude/docs/install-cli | sh
```

**Pros:**
- No API key management in code
- Authentication via CLI
- Same quality as Claude API

**Cons:**
- CLI startup overhead
- Requires CLI installation and auth
- May have rate limits

---

### 3. Ollama (Local LLM)

**Backend**: `ollama_cli`

Uses Ollama for local LLM execution. Ideal for offline use and privacy.

**Setup:**

1. Install Ollama:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. Download a model:
   ```bash
   ollama pull llama2
   # or
   ollama pull mistral
   ```

3. Configure:
   ```env
   LLM_BACKEND=ollama_cli
   OLLAMA_CLI_PATH=ollama
   OLLAMA_MODEL=llama2
   # OPENAI_API_KEY is not required
   ```

**Docker Setup:**

1. Uncomment Ollama installation in `Dockerfile`:
   ```dockerfile
   RUN curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. Add Ollama service to `docker-compose.yml`:
   ```yaml
   ollama:
     image: ollama/ollama:latest
     ports:
       - "11434:11434"
     volumes:
       - ollama_data:/root/.ollama
   ```

**Pros:**
- Free (no API costs)
- Offline capable
- Privacy (data never leaves your machine)
- No API key required

**Cons:**
- Requires local GPU/CPU resources
- Quality may vary by model
- Slower than API calls
- JSON mode support varies by model

---

## Switching Backends

To switch between backends, simply update your `.env` file:

```env
# Use OpenAI API
LLM_BACKEND=openai_api
OPENAI_API_KEY=sk-xxxxx

# Or use Claude CLI
# LLM_BACKEND=claude_cli
# CLAUDE_CLI_PATH=claude

# Or use Ollama
# LLM_BACKEND=ollama_cli
# OLLAMA_CLI_PATH=ollama
# OLLAMA_MODEL=llama2
```

Then restart the application:
```bash
docker-compose restart api
```

---

## Architecture

### Provider Pattern

The LLM service uses the Provider pattern for abstraction:

```
app/services/
├── llm.py                  # Main entry point (call_llm_json)
├── llm_provider.py         # Abstract base class
├── openai_provider.py      # OpenAI API implementation
└── cli_provider.py         # CLI implementations (Claude, Ollama)
```

### Flow

```
User Request
    ↓
call_llm_json() in llm.py
    ↓
get_llm_provider() (factory)
    ↓
LLMProvider.call_json()
    ↓
Backend-specific implementation
```

---

## Cost Comparison

**Monthly costs for 1 user, 100 requests/day:**

| Backend | Cost | Notes |
|---------|------|-------|
| OpenAI API (gpt-4o-mini) | ~$0.14 | Pay per token |
| Claude CLI | Varies | Based on CLI pricing |
| Ollama (Local) | $0 | Hardware costs only |

---

## Testing Backends

Test each backend with a simple extraction:

```bash
# OpenAI API
curl -X POST http://localhost:8000/api/chat/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "明日までにレポートを完成させる"}'

# Check logs
docker-compose logs api | grep "LLM"
```

You should see:
```
Initializing LLM provider, backend=openai_api
Calling LLM, backend=openai_api, model=gpt-4o-mini
LLM call successful
```

---

## Troubleshooting

### OpenAI API

**Error**: `OPENAI_API_KEY is not set`
- Solution: Set `OPENAI_API_KEY` in `.env`

**Error**: `Rate limit exceeded`
- Solution: Wait or upgrade OpenAI plan

### Claude CLI

**Error**: `Claude CLI not found`
- Solution: Install CLI and ensure `CLAUDE_CLI_PATH` is correct

**Error**: `Not authenticated`
- Solution: Run `claude auth login`

### Ollama

**Error**: `Ollama CLI not found`
- Solution: Install Ollama and ensure `OLLAMA_CLI_PATH` is correct

**Error**: `Model not found`
- Solution: Run `ollama pull <model-name>`

---

## Future Backends

Planned support for:
- [ ] Azure OpenAI
- [ ] Google Gemini
- [ ] Anthropic API (direct)
- [ ] LM Studio
- [ ] Custom HTTP endpoints

To request a backend, open an issue on GitHub.
