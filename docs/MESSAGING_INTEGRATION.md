# Messaging Platform Integration

MOS (Management Ourselves System) supports integration with multiple messaging platforms, allowing you to create tasks via messaging apps and receive notifications.

Inspired by [molt.bot](https://github.com/anthropics/molt) architecture, but implemented with official platform SDKs for security and stability.

## Supported Platforms

- ✅ **Telegram Bot** (python-telegram-bot)
- ✅ **Slack Bot** (slack-bolt)

## Architecture

```
┌─────────────────────┐
│ Messaging Platforms │
│  (Telegram, Slack)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ MessagingChannel    │  ← Abstract base class
│  (base.py)          │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│Telegram │ │ Slack   │
│Channel  │ │Channel  │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           ▼
┌─────────────────────┐
│ MessagingManager    │  ← Coordinates multiple channels
│  (manager.py)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│MessagingIntegration │  ← Connects to MOS core
│  (integration.py)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   MOS Core          │
│  (Tasks, Actions)   │
└─────────────────────┘
```

## Features

### Task Creation from Messages
- Send a message to create a task
- First line becomes task title
- Remaining text becomes description
- Automatically categorized with medium priority

### Interactive Task Management
- **Complete** - Mark task as done
- **Cancel** - Cancel the task
- **Edit** - Get link to edit in web UI
- **Details** - View full task details

### Notifications
- Task update notifications sent back to original platform
- Reaction support for quick feedback

## Setup Guide

### Telegram Bot Setup

#### 1. Create Bot with BotFather

```
1. Open Telegram and search for @BotFather
2. Send /newbot
3. Follow instructions to choose name and username
4. Copy the API token (e.g., 123456:ABC-DEF...)
```

#### 2. Get Your User ID

```
1. Search for @userinfobot in Telegram
2. Send /start
3. Copy your User ID (e.g., 123456789)
```

#### 3. Configure MOS

Add to `.env`:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_ALLOWED_USERS=123456789,987654321  # Comma-separated user IDs
```

#### 4. Start MOS

```bash
cd backend
python -m app.main
```

#### 5. Test

```
1. Open Telegram
2. Search for your bot (by username)
3. Send /start
4. Send a message like "Buy groceries"
5. You should receive a task confirmation with buttons
```

### Slack Bot Setup

#### 1. Create Slack App

```
1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch"
4. Enter app name and select workspace
```

#### 2. Configure Bot Token Scopes

Go to "OAuth & Permissions" and add:

**Bot Token Scopes:**
- `chat:write` - Send messages
- `chat:write.public` - Send to public channels
- `reactions:write` - Add reactions
- `users:read` - Read user info
- `channels:read` - Read channel info
- `groups:read` - Read group info
- `im:read` - Read DM info
- `im:history` - Read DM messages
- `mpim:history` - Read group DM messages

#### 3. Enable Socket Mode (Recommended for Local Development)

```
1. Go to "Socket Mode" in sidebar
2. Enable Socket Mode
3. Generate app-level token with "connections:write" scope
4. Copy the token (starts with xapp-)
```

#### 4. Subscribe to Events

Go to "Event Subscriptions":

**Bot Events:**
- `message.channels` - Messages in channels
- `message.groups` - Messages in private channels
- `message.im` - Direct messages

#### 5. Enable Interactivity

Go to "Interactivity & Shortcuts":
- Enable Interactivity
- If using Socket Mode, no Request URL needed

#### 6. Install to Workspace

```
1. Go to "Install App"
2. Click "Install to Workspace"
3. Authorize the app
4. Copy the Bot User OAuth Token (starts with xoxb-)
```

#### 7. Configure MOS

Add to `.env`:

```env
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-...  # Bot User OAuth Token
SLACK_APP_TOKEN=xapp-...  # App-level token (for Socket Mode)
```

#### 8. Start MOS

```bash
cd backend
python -m app.main
```

#### 9. Test

```
1. Open Slack
2. Send a DM to your bot
3. Type "Test task from Slack"
4. You should receive a task confirmation with buttons
```

## Usage Examples

### Creating a Simple Task

**Telegram/Slack:**
```
Buy groceries
```

**Result:**
```
✅ Task created: #123

📋 Buy groceries
📊 Status: TODO
🎯 Priority: MEDIUM

[✓ Complete] [✕ Cancel] [📝 Edit] [🔍 Details]
```

### Creating a Task with Description

**Telegram/Slack:**
```
Prepare presentation
- Create slides
- Add charts
- Practice delivery
```

**Result:**
```
✅ Task created: #124

📋 Prepare presentation
📊 Status: TODO
🎯 Priority: MEDIUM

- Create slides
- Add charts
- Practice delivery

[✓ Complete] [✕ Cancel] [📝 Edit] [🔍 Details]
```

### Completing a Task

Click the **✓ Complete** button on any task message.

**Result:**
```
✅ Task #123 marked as completed!
```

Plus a ✅ reaction on the original message.

## API Reference

### MessagingChannel (Base Class)

Abstract base class for all messaging platforms.

```python
class MessagingChannel(ABC):
    async def send_message(
        self,
        chat_id: str,
        text: str,
        buttons: Optional[List[MessageButton]] = None,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> str:
        """Send a message and return message ID"""

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        buttons: Optional[List[MessageButton]] = None,
    ) -> None:
        """Edit an existing message"""

    async def delete_message(self, chat_id: str, message_id: str) -> None:
        """Delete a message"""

    async def react_to_message(self, chat_id: str, message_id: str, emoji: str) -> None:
        """React to a message with emoji"""

    def on_message(self, handler: Callable) -> None:
        """Register a message handler"""

    def on_button_click(self, callback_data: str, handler: Callable) -> None:
        """Register a button click handler"""
```

### MessageContext

Context object passed to message handlers.

```python
@dataclass
class MessageContext:
    platform: str              # "telegram" or "slack"
    user_id: str              # Platform-specific user ID
    user_name: str            # User's display name
    chat_id: str              # Chat/channel ID
    message_id: str           # Message ID
    text: str                 # Message text
    is_group: bool            # Is this a group/channel message?
    thread_id: Optional[str]  # Thread ID (if in thread)
    raw_update: Any           # Original platform update object
```

### MessageButton

Button definition for inline buttons.

```python
@dataclass
class MessageButton:
    text: str                       # Button label
    callback_data: Optional[str]    # Callback data (for action buttons)
    url: Optional[str]              # URL (for link buttons)
    style: ButtonStyle              # PRIMARY, SECONDARY, SUCCESS, DANGER
```

### MessagingManager

Manages multiple messaging channels.

```python
manager = MessagingManager()

# Register channels
manager.register_channel(telegram_channel)
manager.register_channel(slack_channel)

# Start all channels
await manager.start_all()

# Broadcast message to multiple platforms
await manager.broadcast_message(
    text="Hello from MOS!",
    chat_ids={
        "telegram": "123456789",
        "slack": "C1234567890"
    }
)

# Stop all channels
await manager.stop_all()
```

## Security Considerations

### Telegram
- **User Allowlist**: Configure `TELEGRAM_ALLOWED_USERS` to restrict bot access
- **Token Security**: Keep `TELEGRAM_BOT_TOKEN` secret and never commit to git

### Slack
- **OAuth Scopes**: Only request necessary scopes
- **Socket Mode**: Use Socket Mode for local development (no public endpoint needed)
- **Token Security**: Keep both `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` secret

### General
- All tokens should be in `.env` and added to `.gitignore`
- Use environment-specific tokens (dev/staging/prod)
- Regularly rotate tokens if compromised

## Troubleshooting

### Telegram

**Bot doesn't respond:**
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify your user ID is in `TELEGRAM_ALLOWED_USERS`
- Check backend logs for errors

**"You are not authorized" message:**
- Your user ID is not in the allowlist
- Get your user ID from @userinfobot
- Add to `TELEGRAM_ALLOWED_USERS` in `.env`
- Restart backend

### Slack

**Bot doesn't receive messages:**
- Verify Socket Mode is enabled
- Check `SLACK_APP_TOKEN` is provided
- Ensure bot is installed to workspace
- Check event subscriptions are configured

**Buttons don't work:**
- Verify Interactivity is enabled
- Check button action handlers are registered
- Look for errors in backend logs

**"No messaging channels configured":**
- At least one of `TELEGRAM_BOT_TOKEN` or `SLACK_BOT_TOKEN` must be set
- Check `.env` file is in correct location
- Restart backend after changing `.env`

## Differences from molt.bot

While inspired by molt.bot's architecture, MOS messaging integration has key differences:

| Feature | molt.bot | MOS |
|---------|----------|-----|
| **Implementation** | TypeScript + Direct APIs | Python + Official SDKs |
| **Telegram** | node-telegram-bot-api | python-telegram-bot |
| **Slack** | @slack/web-api | slack-bolt |
| **Security** | Complex custom auth | Platform SDK security |
| **Local Development** | WebSocket gateway | Socket Mode (Slack), Polling (Telegram) |
| **Task Integration** | Separate bot logic | Integrated with MOS core |

## Future Enhancements

- [ ] Discord integration
- [ ] Microsoft Teams integration
- [ ] WhatsApp Business API integration
- [ ] Rich media support (images, files)
- [ ] Voice message transcription
- [ ] Multi-language support
- [ ] Custom command handlers
- [ ] Thread-based task discussions
- [ ] Task assignment via mentions
- [ ] Calendar integration

## Related Documentation

- [Task Actions](./TASK_ACTIONS.md) - LLM-powered task automation
- [External Notifications](./EXTERNAL_NOTIFICATIONS.md) - LINE/Slack/Discord webhooks
- [API Reference](./API_REFERENCE.md) - REST API documentation

## References

- [molt.bot GitHub](https://github.com/anthropics/molt)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [slack-bolt Python Documentation](https://slack.dev/bolt-python/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Slack API](https://api.slack.com/)
