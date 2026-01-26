# Environment Configuration Guide

## Quick Start

1. **Copy the example file**:
   ```bash
   cp .env.example .env
   ```

2. **Add your API keys** (optional - works in demo mode without them):
   ```bash
   # Edit .env and add your keys
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   GOOGLE_API_KEY=AIza...
   ```

3. **Start the application**:
   ```bash
   just dev-desktop
   ```

## Configuration Options

### Required for Production

- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com/
- `OPENAI_API_KEY` - Get from https://platform.openai.com/api-keys
- `GOOGLE_API_KEY` - Get from https://makersuite.google.com/app/apikey

### Optional (with sensible defaults)

All these have default values and don't need to be changed for basic usage:

#### AI Model Settings
- `ANTHROPIC_MODEL` - Default: `claude-3-5-sonnet-20241022`
- `OPENAI_MODEL` - Default: `gpt-4o`
- `GEMINI_MODEL` - Default: `gemini-1.5-pro`
- `ANTHROPIC_MAX_TOKENS` - Default: `1024`
- `OPENAI_MAX_TOKENS` - Default: `1024`
- `GEMINI_MAX_TOKENS` - Default: `1024`

#### API Endpoints
- `ANTHROPIC_API_URL` - Default: `https://api.anthropic.com/v1/messages`
- `OPENAI_API_URL` - Default: `https://api.openai.com/v1/chat/completions`
- `GEMINI_API_URL` - Default: `https://generativelanguage.googleapis.com/v1beta/models`
- `ANTHROPIC_API_VERSION` - Default: `2023-06-01`

#### System Configuration
- `GATEWAY_ADDRESS` - Default: `http://[::1]:50051`
- `CHAT_CONTEXT_LIMIT` - Default: `10` (number of messages sent as context)
- `DATABASE_URL` - Default: `postgresql://identra:identra@localhost:5432/identra_vault`

## Environment Modes

### Demo Mode (No API Keys)
- Works without any API keys set
- Returns mock responses with helpful messages
- Useful for testing the UI and encryption
- All conversations still encrypted and stored

### Development Mode
- Set one or more API keys to test specific models
- Use local PostgreSQL database
- Enable debug logging with `RUST_LOG=debug`

### Production Mode
- All API keys configured
- Custom model configurations as needed
- Production database connection
- Supabase auth configured (if using)

## Common Configurations

### Testing Claude Only
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
# Leave others empty
```

### Using Custom Models
```bash
ANTHROPIC_MODEL=claude-3-opus-20240229
OPENAI_MODEL=gpt-4-turbo-preview
GEMINI_MODEL=gemini-1.5-flash
```

### Increasing Context Window
```bash
CHAT_CONTEXT_LIMIT=20
ANTHROPIC_MAX_TOKENS=2048
OPENAI_MAX_TOKENS=2048
```

### Local Development
```bash
DATABASE_URL=postgresql://identra:identra@localhost:5432/identra_vault
GATEWAY_ADDRESS=http://[::1]:50051
RUST_LOG=debug
```

### Using Different Gateway
```bash
GATEWAY_ADDRESS=http://localhost:50051
# or
GATEWAY_ADDRESS=https://gateway.example.com:50051
```

## Troubleshooting

### Changes not taking effect
- **Restart the application** - `.env` is loaded at startup
- Verify `.env` is in the **root directory** of the project
- Check for typos in variable names
- Ensure no spaces around `=` in `.env` file

### API key not working
- Verify the key is valid and has credits
- Check API key format (Claude: `sk-ant-`, OpenAI: `sk-`, Gemini: `AIza`)
- Ensure no extra spaces or quotes around the key
- Check API provider's status page for outages

### Connection errors
- Ensure `just dev-gateway` is running
- Verify `GATEWAY_ADDRESS` is correct
- Check PostgreSQL is running with `just db-up`
- Test gateway connectivity: `curl http://[::1]:50051`

## Security Best Practices

✅ **DO**:
- Keep `.env` file in `.gitignore` (already configured)
- Use different API keys for development and production
- Rotate API keys periodically
- Set appropriate rate limits with your API providers

❌ **DON'T**:
- Commit `.env` to version control
- Share API keys in chat or documentation
- Use production keys in development
- Store keys in frontend code

## File Locations

```
identra/
├── .env                 # Your configuration (gitignored)
├── .env.example         # Template with all options
└── clients/
    └── ghost-desktop/
        └── src-tauri/
            └── src/
                ├── lib.rs        # Loads .env at startup
                ├── commands.rs   # Uses env vars for AI APIs
                └── grpc_client.rs # Uses env var for gateway
```

## Migration from Environment Variables

If you were previously using direct environment exports:

**Old way** (still works but not recommended):
```bash
export ANTHROPIC_API_KEY="..."
```

**New way** (recommended):
```bash
# Add to .env file
ANTHROPIC_API_KEY=...
```

Both methods work, but `.env` file is preferred for:
- Easier management
- Better documentation
- Consistent across team
- No need to export before each run
