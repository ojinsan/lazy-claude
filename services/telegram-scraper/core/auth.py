"""Authentication helpers for Telegram OTP."""
from __future__ import annotations

import asyncio
from telethon import TelegramClient


async def request_otp_via_bot(
    bot_token: str,
    bot_chat_id: int,
    api_id: int,
    api_hash: str,
    prompt_message: str = "Please enter Telegram OTP:",
    timeout: int = 120,
) -> str | None:
    """
    Request OTP via Telegram bot.

    Sends a prompt to the specified chat and waits for a reply.
    Returns the OTP code or None if timeout.
    """
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    # Create a temporary bot client with real API credentials
    bot = TelegramClient(StringSession(), api_id=api_id, api_hash=api_hash)
    await bot.start(bot_token=bot_token)

    try:
        # Send prompt message
        await bot.send_message(bot_chat_id, prompt_message)

        # Wait for reply
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            async for message in bot.iter_messages(bot_chat_id, limit=5):
                # Check if this is a recent reply (within last 30 seconds)
                if message.out:  # Skip our own messages
                    continue
                msg_age = asyncio.get_event_loop().time() - message.date.timestamp()
                if msg_age < 30 and message.text:
                    # Extract digits only
                    code = "".join(c for c in message.text if c.isdigit())
                    if len(code) >= 5:  # Telegram codes are typically 5 digits
                        return code
            await asyncio.sleep(2)

        return None
    finally:
        await bot.disconnect()


async def request_otp_stdin(prompt: str = "Enter OTP code: ") -> str:
    """Request OTP via stdin (blocking)."""
    import sys

    print(prompt, end="", flush=True)
    loop = asyncio.get_event_loop()
    code = await loop.run_in_executor(None, sys.stdin.readline)
    return code.strip()


async def ensure_authorized(
    client: TelegramClient,
    phone: str,
    password: str | None = None,
    bot_token: str | None = None,
    bot_chat_id: int | None = None,
    api_id: int | None = None,
    api_hash: str | None = None,
) -> bool:
    """
    Ensure the client is authorized.

    Handles login flow with OTP via bot or stdin.
    Returns True if authorized, False otherwise.
    """
    if await client.is_user_authorized():
        return True

    # Request code
    await client.send_code_request(phone)

    # Get OTP
    code = None
    if bot_token and bot_chat_id and api_id and api_hash:
        print("Requesting OTP via Telegram bot...")
        try:
            code = await request_otp_via_bot(
                bot_token,
                bot_chat_id,
                api_id,
                api_hash,
                f"Telegram login OTP requested for {phone}. Reply with the code:",
            )
        except Exception as e:
            print(f"Bot OTP failed: {e}")
            code = None

    if not code:
        print("Using stdin for OTP...")
        code = await request_otp_stdin("Enter Telegram OTP code: ")

    if not code:
        print("No OTP provided")
        return False

    try:
        await client.sign_in(phone, code)
    except Exception as e:
        if "Two-steps verification" in str(e) or "password" in str(e).lower():
            if password:
                await client.sign_in(password=password)
            else:
                pwd = await request_otp_stdin("Enter 2FA password: ")
                await client.sign_in(password=pwd)
        else:
            raise

    return await client.is_user_authorized()
