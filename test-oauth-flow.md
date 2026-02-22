# OAuth Flow Testing Guide

## Prerequisites
1. Bot must be running without errors
2. Have a valid `credentials.json` file ready
3. Know your Telegram user ID

## Test Steps

### Step 1: Start Bot
```
/start
```
Expected: Welcome message with "Add Account" button

### Step 2: Click "Add Account"
Expected: Message asking to upload credentials.json

### Step 3: Upload credentials.json
Expected: 
- Message confirming file received
- Authorization link provided
- Instructions to click link and paste auth code

### Step 4: Click Authorization Link
Expected:
- Opens Google OAuth consent screen
- Shows app name and permissions
- Allows account selection

### Step 5: Authorize and Copy Code
Expected:
- After authorization, shows auth code
- Copy the code

### Step 6: Paste Auth Code in Telegram
Expected:
- Bot processes the code
- Shows success message
- Account added to database
- Returns to main menu

## Debugging

### If OAuth fails at Step 3 (credentials upload):
- Check logs: `podman logs autoxmail_bot | grep -i oauth`
- Verify credentials.json is valid JSON
- Check if document handler is registered

### If OAuth fails at Step 6 (auth code):
- Check if `oauth_text_handler` is being called
- Verify `state == 'waiting_auth_code'` in user_data
- Check logs for ContextTypes errors

### Common Errors

#### ContextTypes not defined
```
NameError: name 'ContextTypes' is not defined
```
**Solution:** Container has old code. Rebuild:
```bash
podman stop autoxmail_bot
podman rm autoxmail_bot
podman rmi localhost/autoxmail-bot:latest
bash setup.sh
```

#### Handler not responding
**Solution:** Check handler registration order in main.py
- OAuth handlers should be in group=0 (highest priority)
- Text handlers should check state before processing

#### State not set
**Solution:** Verify `context.user_data['state'] = 'waiting_auth_code'` is set after credentials upload

## Verification Commands

### Check container status
```bash
podman ps --filter name=autoxmail_bot
```

### Check recent logs
```bash
podman logs --tail 50 autoxmail_bot
```

### Check for errors
```bash
podman logs autoxmail_bot 2>&1 | grep -i error
```

### Restart container
```bash
podman restart autoxmail_bot
```

## Expected Log Output

### Successful OAuth Flow
```
INFO - Starting AutoXMail Bot...
INFO - Bot started successfully!
INFO - User [user_id] uploaded credentials.json
INFO - OAuth flow started for user [user_id]
INFO - User [user_id] authorized account [email]
INFO - Account [email] added successfully
```

### Failed OAuth Flow
```
ERROR - ContextTypes not defined
ERROR - Handler not found for text message
ERROR - Invalid auth code
ERROR - Failed to exchange auth code for token
```
