from __future__ import annotations

import threading
import time
from collections import deque

from core.presenter_v2 import PresenterV2
from core.product_store import ProductStore
from core.tiktok_monitor import TikTokMonitor


class AGCNVoiceRuntime:
    """V0.6.1 Presenter Brain — conversa sem virar tira-dúvidas."""

    MAX_REACTIVE_BURST = 3
    FORCED_PRODUCT_SECONDS = 30.0

    def __init__(self, store: ProductStore | None = None):
        self.store = store or ProductStore()
        self.lock = threading.RLock()

        self.comments = deque(maxlen=30)
        self.comments_analyzed = 0
        self.items_queued = 0
        self.speeches_generated = 0
        self.proactive_generated = 0
        self.interruptions = 0

        self.last_comment = None
        self.last_decision = None
        self.current_speech = None
        self.current_speech_until = 0.0
        self.reactive_streak = 0
        self.forced_product_start_at = 0.0
        self.forced_product_until = 0.0

        active = self.store.active_for_presenter() or {}
        self.presenter = PresenterV2(active)
        self.product_signature = self._product_signature(active)

        self.monitor = TikTokMonitor(
            event_callback=self._on_monitor_event
        )

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
                self.presenter = PresenterV2(active)
                self.current_speech = None
                self.current_speech_until = 0.0
                self.last_decision = None
                self.reactive_streak = 0
                self.forced_product_start_at = 0.0
                self.forced_product_until = 0.0

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
        return self.monitor.start(username)

    def stop(self) -> dict:
        return self.monitor.stop()

    def _product_window_active(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now

        if (
            self.forced_product_until
            and now >= self.forced_product_until
        ):
            self.reactive_streak = 0
            self.forced_product_start_at = 0.0
            self.forced_product_until = 0.0
            return False

        return bool(
            self.forced_product_start_at
            and self.forced_product_start_at <= now < self.forced_product_until
        )

    def _seconds_until_comments(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        if not self.forced_product_until:
            return 0
        if now < self.forced_product_start_at:
            return int(round(
                (self.forced_product_start_at - now)
                + self.FORCED_PRODUCT_SECONDS
            ))
        if self._product_window_active(now):
            return max(0, int(round(self.forced_product_until - now)))
        return 0

    def _schedule_product_window_after(self, speech_until: float) -> None:
        self.forced_product_start_at = speech_until
        self.forced_product_until = (
            speech_until + self.FORCED_PRODUCT_SECONDS
        )

    def _tick_presenter_locked(self):
        self._sync_active_product_locked()

        monitor_state = self.monitor.snapshot()
        if not (
            monitor_state.get("monitoring")
            and monitor_state.get("status") == "ativo"
        ):
            return

        # Comentários continuam sendo analisados e agrupados mesmo quando
        # estamos nos 30s obrigatórios de produto. Eles só aguardam na fila.
        created = self.presenter.process_pending_comments()
        if created:
            self.items_queued += len(created)

        now = time.time()
        product_window = self._product_window_active(now)
        queue = self.presenter.queue_snapshot()

        if self.current_speech and now < self.current_speech_until:
            # Durante o modo produto — e depois da 3ª resposta consecutiva —
            # pergunta nenhuma interrompe a apresentadora.
            if product_window or self.reactive_streak >= self.MAX_REACTIVE_BURST:
                return

            if (
                queue
                and queue[0].get("priority", 0) >= 90
                and queue[0].get("priority", 0)
                > self.current_speech.get("priority", 0)
            ):
                self.current_speech_until = 0.0
                self.interruptions += 1
            else:
                return

        self.current_speech = None
        now = time.time()
        product_window = self._product_window_active(now)

        if product_window:
            # Fala do produto tem prioridade absoluta. A fila de comentários
            # fica intacta até terminar a janela.
            item = self.presenter.force_proactive()
            if item:
                self.proactive_generated += 1
        else:
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
            self.reactive_streak += 1
        elif not product_window:
            # Uma fala espontânea de produto fora da janela também quebra uma
            # sequência curta de perguntas.
            self.reactive_streak = 0

        # Simulação textual da duração. O TTS real/voz local usa a mesma
        # decisão do core e poderá substituir esta estimativa.
        duration = min(
            12.0,
            max(2.5, len(item["speech"]) / 16.0),
        )
        self.current_speech_until = now + duration

        if (
            item.get("type") == "reactive"
            and self.reactive_streak >= self.MAX_REACTIVE_BURST
            and not self.forced_product_until
        ):
            self._schedule_product_window_after(
                self.current_speech_until
            )

    def snapshot(self) -> dict:
        with self.lock:
            self._tick_presenter_locked()

            live = self.monitor.snapshot()
            active = self.store.active() or {}
            presenter_state = self.presenter.snapshot()
            now = time.time()
            paused_seconds = self._seconds_until_comments(now)
            product_mode = self._product_window_active(now)

            data = {
                **live,
                "version": "0.6.1-natural-presenter",
                "products": self.store.list(),
                "active_product": active,
                "comments_analyzed": self.comments_analyzed,
                "items_queued": self.items_queued,
                "speeches_generated": self.speeches_generated,
                "proactive_generated": self.proactive_generated,
                "interruptions": self.interruptions,
                "presenter_mode": (
                    "produto" if product_mode else "interativo"
                ),
                "comments_paused_seconds": paused_seconds,
                "reactive_streak": self.reactive_streak,
                "max_reactive_burst": self.MAX_REACTIVE_BURST,
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
            "AGCN LIVE VOICE — TESTE V0.6.1 NATURAL PRESENTER",
            "",
            f"LIVE: {data.get('username') or 'NÃO INICIADA'}",
            f"Status: {data.get('status', '—')}",
            f"Room ID: {data.get('room_id') or 'NÃO RECEBIDO'}",
            f"Produto ativo: {product.get('name') or 'NÃO CARREGADO'}",
            f"Modo: {data.get('presenter_mode', '—')}",
            f"Respostas seguidas: {data.get('reactive_streak', 0)}/{data.get('max_reactive_burst', 3)}",
            f"Comentários pausados por: {data.get('comments_paused_seconds', 0)}s",
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

        if data.get("error"):
            lines += ["", f"ERRO: {data.get('error')}"]

        return "\n".join(lines)
