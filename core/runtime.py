from __future__ import annotations

import threading
import time
from collections import deque

from core.presenter_engine import PresenterEngine
from core.product_store import ProductStore
from core.tiktok_monitor import TikTokMonitor


class AGCNVoiceRuntime:
    """Runtime integrado do AGCN Live Voice."""

    IDLE_PROACTIVE_INTERVAL = 12.0

    def __init__(self, store: ProductStore | None = None):
        self.store = store or ProductStore()
        self.lock = threading.RLock()

        self.comments = deque(maxlen=20)
        self.comments_analyzed = 0
        self.items_queued = 0
        self.speeches_generated = 0
        self.proactive_generated = 0
        self.reactive_generated = 0

        self.last_comment = None
        self.last_decision = None
        self.current_speech = None
        self.current_speech_until = 0.0

        self.presenter = PresenterEngine(
            self.store.active() or {}
        )

        self.monitor = TikTokMonitor(
            event_callback=self._on_monitor_event
        )

    def _sync_active_product_locked(self):
        active = self.store.active() or {}
        current_id = self.presenter.product.get("id")
        active_id = active.get("id")

        if current_id != active_id:
            self.presenter = PresenterEngine(active)
            self.current_speech = None
            self.current_speech_until = 0.0
            self.last_decision = None

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

            decision = self.presenter.enqueue_comment(
                item["user"],
                item["text"],
            )

            if decision:
                self.comments_analyzed += 1
                self.items_queued += 1
                self.last_decision = decision

    def add_product(self, payload: dict) -> dict:
        payload = payload or {}

        product = self.store.add(
            name=payload.get("name"),
            description=payload.get("description", ""),
            regular_price=payload.get("regular_price"),
            current_price=payload.get("current_price"),
            discount=payload.get("discount"),
            additional_info=payload.get("additional_info", ""),
            category=payload.get("category", ""),
            image_url=payload.get("image_url", ""),
        )

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

    def start(self, username: str) -> dict:
        if not self.store.active():
            return {
                "ok": False,
                "message": "Cadastre e ative um produto antes de iniciar.",
            }
        return self.monitor.start(username)

    def stop(self) -> dict:
        return self.monitor.stop()

    @staticmethod
    def _speech_duration(text: str) -> float:
        # Aproxima a duração da fala para que o planejador não troque de
        # frase antes de a voz terminar. Mantém a simulação responsiva.
        return min(13.0, max(4.0, len(text or "") / 15.0))

    def _select_next_speech_locked(self, now: float) -> dict | None:
        # Depois de um bloco de respostas, comentários ficam temporariamente
        # pausados. Durante essa janela a prioridade absoluta é vender e
        # apresentar o produto, mesmo que a fila continue recebendo perguntas.
        if self.presenter.in_forced_sales_window(now):
            self.proactive_generated += 1
            return self.presenter.build_proactive(now)

        # Fora da janela de produto, responde comentários relevantes com limite
        # de sequência. A própria PresenterEngine abre a janela obrigatória
        # após o número máximo de respostas consecutivas.
        if self.presenter.can_take_reactive(now):
            reactive = self.presenter.next_reactive()
            if reactive:
                self.reactive_generated += 1
                return reactive

        # Sem pergunta para responder, a apresentadora não fica esperando em
        # silêncio: retoma o produto em ritmo de LIVE.
        if now - self.presenter.last_proactive_at >= self.IDLE_PROACTIVE_INTERVAL:
            self.proactive_generated += 1
            return self.presenter.build_proactive(now)

        return None

    def _tick_presenter_locked(self):
        self._sync_active_product_locked()

        monitor_state = self.monitor.snapshot()
        if not (
            monitor_state.get("monitoring")
            and monitor_state.get("status") == "ativo"
        ):
            return

        now = time.time()

        if self.current_speech and now < self.current_speech_until:
            return

        self.current_speech = None
        item = self._select_next_speech_locked(now)

        if not item:
            return

        duration = self._speech_duration(item["speech"])
        speech_until = now + duration

        self.current_speech = item
        self.current_speech_until = speech_until
        self.speeches_generated += 1

        self.presenter.mark_spoken(
            item,
            now=now,
            speech_until=speech_until,
        )

    def snapshot(self) -> dict:
        with self.lock:
            self._tick_presenter_locked()

            live = self.monitor.snapshot()
            active = self.store.active() or {}
            now = time.time()
            comments_paused = self.presenter.seconds_until_reactive(now)

            data = {
                **live,
                "products": self.store.list(),
                "active_product": active,
                "comments_analyzed": self.comments_analyzed,
                "items_queued": self.items_queued,
                "speeches_generated": self.speeches_generated,
                "proactive_generated": self.proactive_generated,
                "reactive_generated": self.reactive_generated,
                "presenter_mode": (
                    "produto" if comments_paused > 0 else "interativo"
                ),
                "comments_paused_seconds": comments_paused,
                "reactive_streak": self.presenter.reactive_streak,
                "max_reactive_burst": self.presenter.MAX_REACTIVE_BURST,
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
                    for item in list(self.comments)[-8:]
                ],
            }

            data["summary"] = self._summary(data)
            return data

    @staticmethod
    def _summary(data: dict) -> str:
        product = data.get("active_product") or {}

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
            "AGCN LIVE VOICE — RESULTADO DO TESTE",
            "",
            f"LIVE: {data.get('username') or 'NÃO INICIADA'}",
            f"Status: {data.get('status', '—')}",
            f"Room ID: {data.get('room_id') or 'NÃO RECEBIDO'}",
            f"Produto ativo: {product.get('name') or 'NÃO CARREGADO'}",
            f"Modo do apresentador: {data.get('presenter_mode', '—')}",
            f"Respostas consecutivas: {data.get('reactive_streak', 0)}/{data.get('max_reactive_burst', 3)}",
            f"Pausa de comentários: {data.get('comments_paused_seconds', 0)}s",
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
            f"Comentários relevantes analisados: {data.get('comments_analyzed', 0)}",
            f"Itens colocados na fila: {data.get('items_queued', 0)}",
            f"Falas sugeridas geradas: {data.get('speeches_generated', 0)}",
            f"Respostas a comentários: {data.get('reactive_generated', 0)}",
            f"Falas proativas de produto: {data.get('proactive_generated', 0)}",
        ]

        decision = data.get("last_decision")
        if decision:
            lines += [
                "",
                f"Comentário que gerou a última decisão: {decision.get('user', '')}: {decision.get('comment', '')}",
                f"Última classificação: {decision.get('label', '—')}",
                f"Última prioridade: {decision.get('priority', '—')}",
            ]

        lines += [
            "",
            f"Resultado automático: {passed}/{len(checks)} verificações confirmadas.",
            f"Diagnóstico: {data.get('diagnostic', '—')}",
        ]

        if data.get("error"):
            lines += ["", f"ERRO: {data.get('error')}"]

        return "\n".join(lines)
