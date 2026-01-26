# Chat Interface Setup Guide

## Overview

The Identra chat interface now supports real AI conversations with Claude, GPT-4, and Gemini models. The chat integration is fully implemented with encrypted storage of all conversations.

## Features Implemented

✅ **Multi-Model Support**: Switch between Claude 3.5 Sonnet, GPT-4o, and Gemini 1.5 Pro
✅ **Real AI Responses**: Actual API calls to Anthropic, OpenAI, and Google AI
✅ **Encrypted Storage**: All conversations are encrypted using AES-256-GCM and stored in the vault
✅ **Conversation History**: Load previous conversations with full encryption/decryption
✅ **Context Management**: Last 10 messages are sent as context for continuity
✅ **Demo Mode**: Works without API keys (shows demo responses)

## Setup Instructions

### 1. Set Up Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# AI Model API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
GOOGLE_API_KEY=your-google-api-key-here
```

**Note**: You can leave the API keys empty to use demo mode with mock responses.

### 2. Get API Keys

- **Anthropic Claude**: https://console.anthropic.com/
- **OpenAI GPT-4**: https://platform.openai.com/api-keys
- **Google Gemini**: https://makersuite.google.com/app/apikey

### 3. Run the Application

```bash
# From the root directory
just dev-desktop

# Or from clients/ghost-desktop/
yarn tauri dev
```

## Configuration

All settings are managed through the `.env` file:

### Customizing API Settings

You can customize the AI models and API endpoints:

```bash
# Use different Claude model
ANTHROPIC_MODEL=claude-3-opus-20240229

# Adjust token limits
ANTHROPIC_MAX_TOKENS=2048
OPENAI_MAX_TOKENS=2048

# Change context window
CHAT_CONTEXT_LIMIT=20  # Include last 20 messages

# Use different gateway address
GATEWAY_ADDRESS=http://localhost:50051
```

See `.env.example` for all available configuration options.

---

## How It Works

### Architecture

```
User Input → ChatInterface.jsx 
    ↓
chat_with_ai (Tauri Command)
    ↓
LLM API (Claude/GPT/Gemini)
    ↓
Store Encrypted Conversation
    ↓
Display AI Response
```

### Backend (Rust)

- **File**: `clients/ghost-desktop/src-tauri/src/commands.rs`
- **Command**: `chat_with_ai`
- **Functions**:
  - `call_claude_api()` - Calls Anthropic Claude API
  - `call_openai_api()` - Calls OpenAI GPT-4 API
  - `call_gemini_api()` - Calls Google Gemini API
  - `store_chat_interaction()` - Encrypts and stores conversations

### Frontend (React)

- **File**: `clients/ghost-desktop/src/pages/ChatInterface.jsx`
- **Features**:
  - Model selector (Claude/GPT/Gemini)
  - Message input with auto-resize
  - Conversation history sidebar
  - Loading states and error handling

### Data Storage

All conversations are stored in PostgreSQL with:
- **Encryption**: AES-256-GCM using session key
- **Metadata**: Model used, timestamp, type
- **Tags**: "chat" tag for easy filtering
- **Format**: JSON with user message, AI response, and model info

## Demo Mode

If no API keys are set, the chat works in demo mode:
- Returns mock responses indicating API key is needed
- Still encrypts and stores conversations
- Useful for testing the UI without API costs

## Testing

### Test Basic Chat
1. Start the app with `just dev-desktop`
2. Type a message and press Enter or click Send
3. You should see a demo response (or real AI if keys are set)

### Test Model Switching
1. Click "Reasoning Engine" dropdown
2. Select different model (Claude/GPT/Gemini)
3. Send a message - response should indicate the selected model

### Test Conversation History
1. Send a few messages
2. Check the "Recent Chats" sidebar
3. Click on a conversation to load it
4. Verify both user and AI messages appear

### Test Encryption
1. Send a message and get a response
2. Check the database (messages are encrypted)
3. Load the conversation - it should decrypt correctly

## Troubleshooting

### "Demo Response" appears even with API key set
- Ensure API key is correctly set in `.env` file
- Verify `.env` file is in the root directory of the project
- Restart the Tauri app after updating `.env`
- Check the terminal for environment variable loading logs

### "Failed to connect to gateway" error
- Start the tunnel-gateway service: `just dev-gateway`
- Ensure PostgreSQL is running: `just db-up`
- Check that gateway is listening on `[::1]:50051`

### API errors
- Verify API key is valid and has credits
- Check API rate limits
- Review terminal logs for detailed error messages

### Conversation history not loading
- Ensure session is initialized (green indicator at bottom)
- Check that gateway service is running
- Verify database has `memories` table

## Next Steps

### Planned Improvements
- [ ] Streaming responses for real-time output
- [ ] Message editing and regeneration
- [ ] Export conversations
- [ ] Search across all conversations
- [ ] Custom system prompts per model
- [ ] Token usage tracking
- [ ] Cost estimation

### Development Notes
- All LLM calls go through Tauri commands (no direct frontend API calls)
- Conversations are encrypted before storage
- Frontend maintains local state for current chat
- History is fetched from database on load
