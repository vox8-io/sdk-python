"""vox8 client for real-time speech translation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable, Literal

import websockets

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection


VoiceMode = Literal["match", "male", "female"]


class Vox8Client:
    """
    Client for connecting to vox8 real-time speech translation API.

    Authentication:
        Use ONE of:
        - api_key: For server-side usage (recommended for Python)
        - session_token: For when you have a pre-generated session token

    Example:
        >>> from vox8 import Vox8Client
        >>> import asyncio
        >>> import base64
        >>>
        >>> client = Vox8Client(
        ...     api_key="vox8_xxx",
        ...     target_language="es",
        ...     on_transcript=lambda evt: print(evt["text"], evt.get("translation")),
        ... )
        >>>
        >>> async def main():
        ...     await client.connect()
        ...     asyncio.create_task(client.listen())
        ...     # Send audio chunks
        ...     await client.send_audio(base64.b64encode(audio_bytes).decode())
        ...     await client.disconnect()
        >>>
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        target_language: str,
        *,
        api_key: str | None = None,
        session_token: str | None = None,
        source_language: str = "auto",
        voice_mode: VoiceMode = "match",
        ws_url: str = "wss://api.vox8.io/v1/translate",
        on_transcript: Callable[[dict[str, Any]], None] | None = None,
        on_audio: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """
        Initialize the vox8 client.

        Args:
            target_language: Target language code (e.g., 'es', 'fr', 'de')
            api_key: Your vox8 API key (for server-side usage)
            session_token: Session token (alternative to api_key)
            source_language: Source language code or 'auto' for detection
            voice_mode: Voice mode - 'match' preserves speaker voice
            ws_url: WebSocket URL (default: wss://api.vox8.io/v1/translate)
            on_transcript: Callback for transcript events
            on_audio: Callback for audio events
            on_error: Callback for error events

        Raises:
            ValueError: If neither api_key nor session_token is provided
        """
        if not api_key and not session_token:
            raise ValueError("Either api_key or session_token must be provided")

        self.api_key = api_key
        self.session_token = session_token
        self.target_language = target_language
        self.source_language = source_language
        self.voice_mode = voice_mode
        self.ws_url = ws_url
        self.on_transcript = on_transcript
        self.on_audio = on_audio
        self.on_error = on_error
        self._ws: ClientConnection | None = None
        self._session_id: str | None = None

    @property
    def is_connected(self) -> bool:
        """Whether the client is connected to vox8."""
        return self._ws is not None and self._ws.state.name == "OPEN"

    @property
    def session_id(self) -> str | None:
        """Current session ID, if connected."""
        return self._session_id

    async def connect(self) -> None:
        """
        Connect to vox8 and start a translation session.

        Raises:
            RuntimeError: If already connected
            websockets.exceptions.WebSocketException: If connection fails
        """
        if self._ws is not None:
            raise RuntimeError("Already connected")

        self._ws = await websockets.connect(self.ws_url)

        # Build session_start message with appropriate auth
        session_start: dict[str, Any] = {
            "type": "session_start",
            "target_language": self.target_language,
            "source_language": self.source_language,
            "voice_mode": self.voice_mode,
            "audio_format": "pcm_s16le",
        }

        # Use session token or API key
        if self.session_token:
            session_start["session_token"] = self.session_token
        elif self.api_key:
            session_start["api_key"] = self.api_key

        await self._ws.send(json.dumps(session_start))

    async def listen(self) -> None:
        """
        Listen for messages from vox8 and dispatch to callbacks.

        This method runs until the connection is closed.
        Should be run as a background task.

        Raises:
            RuntimeError: If not connected
        """
        if self._ws is None:
            raise RuntimeError("Not connected")

        async for message in self._ws:
            event = json.loads(message)
            self._handle_event(event)

    async def send_audio(self, audio_base64: str) -> None:
        """
        Send audio data to vox8 for translation.

        Args:
            audio_base64: Base64-encoded PCM audio (16kHz, mono, 16-bit signed LE)

        Raises:
            RuntimeError: If not connected
        """
        if self._ws is None:
            raise RuntimeError("Not connected")

        await self._ws.send(json.dumps({"type": "audio", "audio": audio_base64}))

    async def send_keepalive(self) -> None:
        """
        Send a keepalive message to prevent session timeout.

        Call this every 15 seconds when not sending audio.

        Raises:
            RuntimeError: If not connected
        """
        if self._ws is None:
            raise RuntimeError("Not connected")

        await self._ws.send(json.dumps({"type": "keepalive"}))

    async def disconnect(self) -> None:
        """Gracefully end the session and close the connection."""
        if self._ws is not None:
            try:
                await self._ws.send(json.dumps({"type": "session_end"}))
                await self._ws.close()
            finally:
                self._ws = None
                self._session_id = None

    def _handle_event(self, event: dict[str, Any]) -> None:
        """Handle an event from vox8."""
        event_type = event.get("type")

        if event_type == "session_ready":
            self._session_id = event.get("session_id")

        elif event_type == "transcript" and self.on_transcript:
            self.on_transcript(event)

        elif event_type == "audio" and self.on_audio:
            self.on_audio(event)

        elif event_type == "error" and self.on_error:
            self.on_error(event)
