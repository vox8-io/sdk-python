# vox8

Python SDK for vox8 real-time speech translation.

## Installation

```bash
pip install vox8
```

## Authentication

The SDK supports two authentication methods:

| Method | Use case | Security |
|--------|----------|----------|
| `api_key` | Server-side Python apps | Recommended for Python |
| `session_token` | Pre-generated token | Alternative auth method |

Since Python typically runs server-side, using `api_key` directly is secure.

## Basic usage

```python
from vox8 import Vox8Client
import asyncio
import base64

client = Vox8Client(
    api_key="vox8_xxx",
    target_language="es",
    on_transcript=lambda evt: print(f"{evt['text']} → {evt.get('translation', '')}"),
    on_audio=lambda evt: print(f"Received audio: {len(evt['audio'])} bytes"),
)

async def main():
    await client.connect()

    # Start listening for responses in background
    listen_task = asyncio.create_task(client.listen())

    # Send audio chunks (16kHz, mono, 16-bit signed LE PCM)
    with open("audio.raw", "rb") as f:
        while chunk := f.read(4096):
            await client.send_audio(base64.b64encode(chunk).decode())
            await asyncio.sleep(0.1)  # ~100ms chunks

    await client.disconnect()

asyncio.run(main())
```

## With microphone input

```python
from vox8 import Vox8Client
import asyncio
import base64
import pyaudio

client = Vox8Client(
    api_key="vox8_xxx",
    target_language="es",
    on_transcript=lambda evt: print(evt["text"], "→", evt.get("translation", "")),
)

async def main():
    await client.connect()
    asyncio.create_task(client.listen())

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=4096,
    )

    try:
        while True:
            data = stream.read(4096, exception_on_overflow=False)
            await client.send_audio(base64.b64encode(data).decode())
    except KeyboardInterrupt:
        pass
    finally:
        stream.close()
        pa.terminate()
        await client.disconnect()

asyncio.run(main())
```

## Using session tokens

If you have a pre-generated session token (e.g., from a web backend):

```python
from vox8 import Vox8Client

client = Vox8Client(
    session_token="your_session_token",  # Alternative to api_key
    target_language="es",
)
```

## API

### Vox8Client

```python
client = Vox8Client(
    target_language: str,                # Target language code (e.g., 'es', 'fr')
    api_key: str | None = None,          # Your vox8 API key
    session_token: str | None = None,    # Alternative: session token
    source_language: str = "auto",       # Source language or 'auto'
    voice_mode: str = "match",           # 'match', 'male', or 'female'
    ws_url: str = "wss://api.vox8.io/v1/translate",
    on_transcript: Callable | None = None,
    on_audio: Callable | None = None,
    on_error: Callable | None = None,
)
```

Either `api_key` or `session_token` must be provided.

### Methods

- `await client.connect()` - Connect to vox8
- `await client.listen()` - Listen for events (run as background task)
- `await client.send_audio(base64_audio)` - Send audio data
- `await client.send_keepalive()` - Prevent session timeout
- `await client.disconnect()` - End session and disconnect

### Properties

- `client.is_connected` - Whether connected
- `client.session_id` - Current session ID

### Events

**Transcript event:**
```python
{
    "type": "transcript",
    "text": "Hello world",
    "is_final": True,
    "translation": "Hola mundo"  # Only present when is_final=True
}
```

**Audio event:**
```python
{
    "type": "audio",
    "audio": "base64_encoded_audio",
    "sequence": 0,
    "original_text": "Hello world",
    "translated_text": "Hola mundo"
}
```

## License

MIT
