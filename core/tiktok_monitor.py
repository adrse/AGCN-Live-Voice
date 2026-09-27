from __future__ import annotations

import asyncio
import re
import threading
import time
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent,
    ConnectEvent,
    DisconnectEvent,
    FollowEvent,
    GiftEvent,
    LikeEvent,
    LiveEndEvent,
    RoomUserSeqEvent,
    ShareEvent,
)


def clean(text) -> str:
    return re.sub(r"\\s+", " ", str(text or "").strip())


class TikTokMonitor:
    """Monitor TikTok LIVE baseado no fluxo validado no Colab."""

    def __init__(self, event_callback=None):
        self.event_callback = event_callback
        self.lock = threading.RLock()
        self.thread = None
        self.loop = None
        self.task = None
        self.client = None
        self.monitoring = False
        self.stop_requested = False
        self.seen_ids = set()
        self.seen_id_order = deque(maxlen=5000)
        self.seen_text = {}
        self._reset_state()

    def _reset_state(self):
        self.username = ""
        self.status = "parado"
        self.error = None
        self.diagnostic = "Aguardando início."
        self.connected = False
        self.room_id = None
        self.viewers = None
        self.total_user = None
        self.likes = None
        self.shares = 0
        self.follows = 0
        self.gifts = 0
        self.comments_received = 0

    @staticmethod
    def normalize_username(value: str) -> str:
        value = clean(value)
        if not value:
            raise ValueError("Informe o @username da LIVE.")
        if "tiktok.com/@" in value:
            value = value.split("tiktok.com/@", 1)[1]
            value = value.split("/", 1)[0]
            value = value.split("?", 1)[0]
        value = value.lstrip("@").strip()
        if not value:
            raise ValueError("Username inválido.")
        return "@" + value

    @staticmethod
    def _user_name(user) -> str:
        return (
            getattr(user, "nickname", None)
            or getattr(user, "unique_id", None)
            or getattr(user, "display_id", None)
            or "Usuário"
        )

    @staticmethod
    def _message_id(event) -> str | None:
        for obj in (getattr(event, "common", None), event):
            if obj is None:
                continue
            for field in ("msg_id", "message_id", "id"):
                value = getattr(obj, field, None)
                if value:
                    return str(value)
        return None

    def _remember_message_id(self, msg_id: str | None):
        if not msg_id or msg_id in self.seen_ids:
            return
        if len(self.seen_id_order) >= self.seen_id_order.maxlen:
            old = self.seen_id_order.popleft()
            self.seen_ids.discard(old)
        self.seen_id_order.append(msg_id)
        self.seen_ids.add(msg_id)

    def _emit(self, event_type: str, payload: dict):
        if self.event_callback:
            self.event_callback(event_type, payload)

    def _install_listeners(self):
        @self.client.on(ConnectEvent)
        async def on_connect(event):
            with self.lock:
                self.connected = True
                self.status = "ativo"
                self.room_id = (
                    str(self.client.room_id)
                    if self.client.room_id is not None
                    else None
                )
                self.diagnostic = "ConnectEvent recebido."
                payload = {
                    "room_id": self.room_id,
                    "username": self.username,
                }
            self._emit("connect", payload)

        @self.client.on(RoomUserSeqEvent)
        async def on_viewers(event):
            payload = {}
            with self.lock:
                total = getattr(event, "total", None)
                total_user = getattr(event, "total_user", None)
                if total is not None:
                    self.viewers = int(total)
                    payload["viewers"] = self.viewers
                if total_user is not None:
                    self.total_user = int(total_user)
                    payload["total_user"] = self.total_user
            if payload:
                self._emit("viewers", payload)

        @self.client.on(LikeEvent)
        async def on_like(event):
            total = getattr(event, "total", None)
            if total is not None:
                with self.lock:
                    self.likes = int(total)
                    payload = {"likes": self.likes}
                self._emit("like", payload)

        @self.client.on(ShareEvent)
        async def on_share(event):
            with self.lock:
                self.shares += 1
                payload = {"shares": self.shares}
            self._emit("share", payload)

        @self.client.on(FollowEvent)
        async def on_follow(event):
            with self.lock:
                self.follows += 1
                payload = {"follows": self.follows}
            self._emit("follow", payload)

        @self.client.on(GiftEvent)
        async def on_gift(event):
            if bool(getattr(event, "streaking", False)):
                return
            repeat_count = getattr(event, "repeat_count", 1) or 1
            try:
                repeat_count = int(repeat_count)
            except Exception:
                repeat_count = 1
            with self.lock:
                self.gifts += max(1, repeat_count)
                payload = {"gifts": self.gifts}
            self._emit("gift", payload)

        @self.client.on(CommentEvent)
        async def on_comment(event):
            text = clean(getattr(event, "comment", ""))
            if not text:
                return

            user = self._user_name(getattr(event, "user", None))
            msg_id = self._message_id(event)
            now_mono = time.monotonic()
            signature = (user.casefold(), text.casefold())

            with self.lock:
                if msg_id and msg_id in self.seen_ids:
                    return

                self._remember_message_id(msg_id)

                if now_mono - self.seen_text.get(signature, -999) <= 5:
                    return

                self.seen_text[signature] = now_mono
                self.seen_text = {
                    key: ts
                    for key, ts in self.seen_text.items()
                    if now_mono - ts <= 60
                }

                self.comments_received += 1
                payload = {
                    "time": datetime.now(
                        ZoneInfo("America/Araguaina")
                    ).strftime("%H:%M:%S"),
                    "user": user,
                    "text": text,
                    "message_id": msg_id,
                    "comments_received": self.comments_received,
                }

            self._emit("comment", payload)

        @self.client.on(LiveEndEvent)
        async def on_live_end(event):
            with self.lock:
                self.connected = False
                self.status = "finalizado"
                self.diagnostic = "A LIVE foi encerrada."
            self._emit("live_end", {})

        @self.client.on(DisconnectEvent)
        async def on_disconnect(event):
            with self.lock:
                self.connected = False
                if self.status not in {"finalizado", "encerrado"}:
                    self.status = "desconectado"
                self.diagnostic = "DisconnectEvent recebido."
            self._emit("disconnect", {})

    async def _monitor_async(self, username: str):
        self.client = TikTokLiveClient(unique_id=username)
        self._install_listeners()

        try:
            with self.lock:
                self.status = "verificando"
                self.diagnostic = "Verificando se a conta está em LIVE."

            is_live = await self.client.is_live()

            if not is_live:
                with self.lock:
                    self.status = "offline"
                    self.error = "A conta não está em LIVE neste momento."
                    self.diagnostic = "is_live=False."
                return

            if self.stop_requested:
                return

            with self.lock:
                self.status = "conectando"
                self.diagnostic = "LIVE encontrada. Abrindo conexão de eventos."

            await self.client.connect()

            with self.lock:
                if (
                    not self.stop_requested
                    and self.status not in {"finalizado", "erro"}
                ):
                    self.status = "finalizado"

        finally:
            try:
                if self.client is not None:
                    await self.client.disconnect()
            except Exception:
                pass

    def _runner(self, username: str):
        loop = asyncio.new_event_loop()
        self.loop = loop
        asyncio.set_event_loop(loop)

        try:
            self.task = loop.create_task(self._monitor_async(username))
            loop.run_until_complete(self.task)

            with self.lock:
                if self.stop_requested:
                    self.status = "encerrado"

        except asyncio.CancelledError:
            with self.lock:
                self.status = "encerrado"

        except BaseException as exc:
            with self.lock:
                self.status = "erro"
                self.error = f"{type(exc).__name__}: {exc}"
                self.diagnostic = "Erro no monitoramento."

        finally:
            try:
                pending = [
                    item
                    for item in asyncio.all_tasks(loop)
                    if not item.done()
                ]
                for item in pending:
                    item.cancel()
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(
                            *pending,
                            return_exceptions=True,
                        )
                    )
            except Exception:
                pass

            try:
                loop.close()
            except Exception:
                pass

            with self.lock:
                self.connected = False
                self.monitoring = False
                if self.status not in {
                    "erro",
                    "offline",
                    "finalizado",
                    "encerrado",
                }:
                    self.status = "encerrado"

    def start(self, value: str) -> dict:
        username = self.normalize_username(value)

        with self.lock:
            if self.monitoring:
                return {
                    "ok": False,
                    "message": "Já existe um monitoramento ativo.",
                }

            self._reset_state()
            self.seen_ids.clear()
            self.seen_id_order.clear()
            self.seen_text.clear()
            self.username = username
            self.monitoring = True
            self.stop_requested = False
            self.status = "iniciando"
            self.error = None
            self.diagnostic = "Thread de monitoramento iniciada."

        self.thread = threading.Thread(
            target=self._runner,
            args=(username,),
            daemon=True,
        )
        self.thread.start()

        return {
            "ok": True,
            "username": username,
            "message": "Monitoramento iniciado.",
        }

    def stop(self) -> dict:
        with self.lock:
            if not self.monitoring:
                self.status = "encerrado"
                return {
                    "ok": True,
                    "message": "O monitoramento já estava parado.",
                }

            self.stop_requested = True
            self.status = "encerrando"
            self.diagnostic = "Encerramento solicitado."
            loop = self.loop
            task = self.task

        if loop is not None and task is not None:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except Exception:
                pass

        return {
            "ok": True,
            "message": "Encerramento solicitado.",
        }

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "monitoring": self.monitoring,
                "username": self.username,
                "status": self.status,
                "error": self.error,
                "diagnostic": self.diagnostic,
                "connected": self.connected,
                "room_id": self.room_id,
                "viewers": self.viewers,
                "total_user": self.total_user,
                "likes": self.likes,
                "shares": self.shares,
                "follows": self.follows,
                "gifts": self.gifts,
                "comments_received": self.comments_received,
            }
