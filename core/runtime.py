from __future__ import annotations

import threading
import time
from collections import deque

from core.brain_factory import build_brain_provider
from core.integration_contracts import BrainProvider
from core.presenter_v2 import PresenterV2
from core.presenter_v3 import PresenterV3
from core.product_store import ProductStore
from core.tiktok_monitor import TikTokMonitor
from core.voice_factory import build_voice_service
from core.voice_service import VoiceService


class AGCNVoiceRuntime:
    """Runtime integrado da LIVE.

    - sem brain_config: mantém PresenterV2 para compatibilidade;
    - com brain_config: usa PresenterV3 + Qwen/API;
    - com voice_config/voice_service: fala aprovada entra na fila TTS e sai
      pelo dispositivo de áudio escolhido (incluindo VB-CABLE).
    """

    def __init__(
        self,
        store: ProductStore | None = None,
        *,
        brain_provider: BrainProvider | None = None,
        brain_config: dict | None = None,
        voice_service: VoiceService | None = None,
        voice_config: dict | None = None,
    ):
        self.store = store or ProductStore()
        self.lock = threading.RLock()

        self.comments = deque(maxlen=30)
        self.comments_analyzed = 0
        self.items_queued = 0
        self.speeches_generated = 0
        self.proactive_generated = 0
        self.interruptions = 0
        self.voice_jobs = 0

        self.last_comment = None
        self.last_decision = None
        self.current_speech = None
        self.current_speech_until = 0.0

        self.brain_provider = brain_provider
        if self.brain_provider is None and brain_config is not None:
            self.brain_provider = build_brain_provider(brain_config)

        self.voice_service = voice_service
        if self.voice_service is None and voice_config is not None:
            self.voice_service = build_voice_service(voice_config)

        active = self.store.active_for_presenter() or {}
        self.presenter = self._new_presenter(active)
        self.product_signature = self._product_signature(active)

        self.monitor = TikTokMonitor(
            event_callback=self._on_monitor_event
        )

    def _new_presenter(self, product: dict):
        if self.brain_provider is not None:
            return PresenterV3(product, self.brain_provider)
        return PresenterV2(product)

    @staticmethod
    def _product_signature(product: dict) -> tuple:
        return (
            product.get("id"),
            product.get("updated_at"),
        )

    def _sync_active_product_locked(self):
        active = self.store.active_for_presenter() or {}
        signature = self._product_signature(active)

        if signature != self.product_signature:
            previous_id = self.presenter.product.get("id")
            active_id = active.get("id")

            if previous_id == active_id:
                self.presenter.set_product(active)
            else:
                self.presenter = self._new_presenter(active)
                self.current_speech = None
                self.current_speech_until = 0.0
                self.last_decision = None

            self.product_signature = signature

    def _on_monitor_event(self, event_type: str, payload: dict):
        if event_type != "comment":
            return

        with self.lock:
            self._sync_active_product_locked()

            item = {
                "time": payload.get("time"),
                "user": payload.get("user"),
                "text": payload.get("text"),
            }

            self.comments.append(item)
            self.last_comment = item

            analyzed = self.presenter.ingest_comment(
                item["user"],
                item["text"],
            )

            if analyzed:
                self.comments_analyzed += 1

    def add_product(self, payload: dict) -> dict:
        product = self.store.add(**(payload or {}))

        with self.lock:
            self._sync_active_product_locked()

        return {
            "ok": True,
            "message": "Produto salvo.",
            "product": product,
        }

    def update_product(self, product_id: str, payload: dict) -> dict:
        product = self.store.update(product_id, **(payload or {}))
        with self.lock:
            self._sync_active_product_locked()
        return {
            "ok": True,
            "message": "Produto atualizado.",
            "product": product,
        }

    def activate_product(self, product_id: str) -> dict:
        product = self.store.activate(product_id)

        with self.lock:
            self._sync_active_product_locked()

        return {
            "ok": True,
            "message": "Produto ativo alterado.",
            "product": product,
        }

    def delete_product(self, product_id: str) -> dict:
        removed = self.store.delete(product_id)

        with self.lock:
            self._sync_active_product_locked()

        return {
            "ok": bool(removed),
            "message": (
                "Produto excluído."
                if removed
                else "Produto não encontrado."
            ),
        }

    def test_presenter_comment(
        self,
        user: str,
        text: str,
    ) -> dict:
        with self.lock:
            self._sync_active_product_locked()
            if not self.presenter.product.get("name"):
                return {
                    "ok": False,
                    "message": "Cadastre e ative um produto antes do teste.",
                }
            return self.presenter.test_comment(user, text)

    def test_presenter_proactive(self) -> dict:
        with self.lock:
            self._sync_active_product_locked()
            if not self.presenter.product.get("name"):
                return {
                    "ok": False,
                    "message": "Cadastre e ative um produto antes do teste.",
                }
            return self.presenter.test_proactive()

    def start(self, username: str) -> dict:
        if not self.store.active():
            return {
                "ok": False,
                "message": "Cadastre e ative um produto antes de iniciar.",
            }

        if self.voice_service is not None:
            self.voice_service.start()

        result = self.monitor.start(username)
        if not result.get("ok", True) and self.voice_service is not None:
            self.voice_service.stop()
        return result

    def stop(self) -> dict:
        result = self.monitor.stop()
        if self.voice_service is not None:
            self.voice_service.stop()
        return result

    def _queue_voice(self, item: dict) -> None:
        if self.voice_service is None:
            return

        if item.get("type") == "reactive":
            # Não corta a frase já sendo reproduzida; apenas remove proativos
            # que ainda aguardavam na fila para responder o chat em seguida.
            self.voice_service.clear_pending(proactive_only=True)

        self.voice_service.enqueue(
            item["speech"],
            priority=int(item.get("priority", 30)),
            metadata={
                "type": item.get("type"),
                "intent": item.get("intent"),
                "topic": item.get("topic"),
                "user": item.get("user"),
                "comment": item.get("comment"),
            },
        )
        self.voice_jobs += 1

    def _tick_presenter_locked(self):
        self._sync_active_product_locked()

        monitor_state = self.monitor.snapshot()
        if not (
            monitor_state.get("monitoring")
            and monitor_state.get("status") == "ativo"
        ):
            return

        created = self.presenter.process_pending_comments()
        if created:
            self.items_queued += len(created)

        queue = self.presenter.queue_snapshot()
        now = time.time()

        if self.current_speech and now < self.current_speech_until:
            if (
                queue
                and queue[0].get("priority", 0) >= 90
                and queue[0].get("priority", 0)
                > self.current_speech.get("priority", 0)
            ):
                # Marca a prioridade para a próxima fala, mas o VoiceService
                # deixa o segmento de áudio corrente terminar naturalmente.
                self.current_speech_until = 0.0
                self.interruptions += 1
            else:
                return

        self.current_speech = None

        proactive = self.presenter.maybe_proactive()
        if proactive:
            self.proactive_generated += 1
            self.items_queued += 1

        item = self.presenter.next_speech()
        if not item:
            return

        self.current_speech = item
        self.speeches_generated += 1

        if item.get("type") == "reactive":
            self.last_decision = item

        try:
            self._queue_voice(item)
        except Exception as exc:
            item["voice_error"] = str(exc)

        # Estimativa apenas para scheduling/UI. Playback real é controlado
        # pelo VoiceService quando configurado.
        duration = min(
            12.0,
            max(2.5, len(item["speech"]) / 16.0),
        )
        self.current_speech_until = now + duration

    def snapshot(self) -> dict:
        with self.lock:
            self._tick_presenter_locked()

            live = self.monitor.snapshot()
            active = self.store.active() or {}
            presenter_state = self.presenter.snapshot()
            voice_state = (
                self.voice_service.snapshot()
                if self.voice_service is not None
                else None
            )

            data = {
                **live,
                "version": (
                    "0.8-brain-voice"
                    if self.brain_provider is not None
                    and self.voice_service is not None
                    else "0.7-llm-brain"
                    if self.brain_provider is not None
                    else "0.6-presenter-brain"
                ),
                "brain_enabled": self.brain_provider is not None,
                "brain_provider": (
                    self.brain_provider.name
                    if self.brain_provider is not None
                    else "deterministic-v2"
                ),
                "voice_enabled": self.voice_service is not None,
                "voice": voice_state,
                "voice_jobs": self.voice_jobs,
                "products": self.store.list(),
                "active_product": active,
                "comments_analyzed": self.comments_analyzed,
                "items_queued": self.items_queued,
                "speeches_generated": self.speeches_generated,
                "proactive_generated": self.proactive_generated,
                "interruptions": self.interruptions,
                "last_comment": (
                    dict(self.last_comment)
                    if self.last_comment
                    else None
                ),
                "last_decision": (
                    dict(self.last_decision)
                    if self.last_decision
                    else None
                ),
                "queue": [
                    dict(item)
                    for item in self.presenter.queue_snapshot()
                ],
                "current_speech": (
                    dict(self.current_speech)
                    if self.current_speech
                    else None
                ),
                "comments": [
                    dict(item)
                    for item in list(self.comments)[-12:]
                ],
                "presenter": presenter_state,
            }

            data["summary"] = self._summary(data)
            return data

    @staticmethod
    def _summary(data: dict) -> str:
        product = data.get("active_product") or {}
        presenter = data.get("presenter") or {}
        memory = presenter.get("memory") or {}
        watchdog = presenter.get("watchdog") or {}
        voice = data.get("voice") or {}

        checks = {
            "LIVE conectou": bool(
                data.get("connected") or data.get("room_id")
            ),
            "Room ID recebido": bool(data.get("room_id")),
            "Produto ativo carregado": bool(product.get("name")),
            "Comentários recebidos": (
                data.get("comments_received", 0) > 0
            ),
            "Comentário analisado/classificado": (
                data.get("comments_analyzed", 0) > 0
            ),
            "Fila de resposta utilizada": (
                data.get("items_queued", 0) > 0
            ),
            "Fala sugerida gerada": (
                data.get("speeches_generated", 0) > 0
            ),
        }

        passed = sum(1 for ok in checks.values() if ok)

        lines = [
            "AGCN LIVE VOICE — TESTE PRESENTER BRAIN",
            "",
            f"LIVE: {data.get('username') or 'NÃO INICIADA'}",
            f"Status: {data.get('status', '—')}",
            f"Room ID: {data.get('room_id') or 'NÃO RECEBIDO'}",
            f"Produto ativo: {product.get('name') or 'NÃO CARREGADO'}",
            f"Brain: {data.get('brain_provider', '—')}",
            f"Voz: {voice.get('tts') or ('DESATIVADA' if not data.get('voice_enabled') else '—')}",
            "",
            "CHECKLIST:",
        ]

        for label, ok in checks.items():
            lines.append(f"{'OK' if ok else 'PENDENTE'} - {label}")

        lines += [
            "",
            f"Viewers atuais: {data.get('viewers') if data.get('viewers') is not None else '—'}",
            f"Curtidas: {data.get('likes') if data.get('likes') is not None else '—'}",
            f"Comentários recebidos: {data.get('comments_received', 0)}",
            f"Comentários analisados: {data.get('comments_analyzed', 0)}",
            f"Itens enfileirados: {data.get('items_queued', 0)}",
            f"Falas geradas: {data.get('speeches_generated', 0)}",
            f"Falas proativas: {data.get('proactive_generated', 0)}",
            f"Jobs de voz: {data.get('voice_jobs', 0)}",
            f"Interrupções prioritárias: {data.get('interruptions', 0)}",
            f"Silêncio atual: {memory.get('seconds_since_speech', '—')}s",
            f"Watchdog: {watchdog.get('status', '—')}",
            f"Tópico atual: {memory.get('current_topic') or '—'}",
        ]

        decision = data.get("last_decision")
        if decision:
            lines += [
                "",
                f"Comentário da última decisão: {decision.get('user', '')}: {decision.get('comment', '')}",
                f"Intenção: {decision.get('label', '—')}",
                f"Prioridade: {decision.get('priority', '—')}",
                f"Plano: {' → '.join(decision.get('plan') or [])}",
            ]

        lines += [
            "",
            f"Resultado automático: {passed}/{len(checks)} verificações confirmadas.",
            f"Diagnóstico TikTok: {data.get('diagnostic', '—')}",
        ]

        if voice.get("last_error"):
            lines += ["", f"ERRO DE VOZ: {voice.get('last_error')}"]
        if data.get("error"):
            lines += ["", f"ERRO: {data.get('error')}"]

        return "\n".join(lines)
