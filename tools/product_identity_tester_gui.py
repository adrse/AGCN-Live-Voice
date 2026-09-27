from __future__ import annotations

import json
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from core.product_research_v054 import ProductResearchEngineV054


APP_TITLE = "AGCN Live Voice — Teste Product Identity"


class ProductIdentityTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x720")
        self.minsize(820, 620)

        self.events = queue.Queue()
        self.last_result = None
        self.engine = None

        self._build_ui()
        self.after(100, self._drain_events)

    def _build_ui(self):
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        ttk.Label(
            root,
            text="AGCN Product Identity — TikTok + Google Lens",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            root,
            text=(
                "Cole um link de produto do TikTok. O teste extrai nome/imagem, "
                "abre o Google Lens no seu computador e procura o mesmo produto."
            ),
            wraplength=900,
        ).pack(anchor="w", pady=(6, 16))

        line = ttk.Frame(root)
        line.pack(fill="x")

        self.url_var = tk.StringVar(
            value="https://vt.tiktok.com/ZS9Av5HLW5A4p-QKM1w/"
        )
        self.url_entry = ttk.Entry(
            line,
            textvariable=self.url_var,
        )
        self.url_entry.pack(
            side="left",
            fill="x",
            expand=True,
        )

        self.button = ttk.Button(
            line,
            text="Analisar produto",
            command=self._start_analysis,
        )
        self.button.pack(
            side="left",
            padx=(10, 0),
        )

        self.status_var = tk.StringVar(
            value="Pronto para testar."
        )
        ttk.Label(
            root,
            textvariable=self.status_var,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(12, 6))

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        self.summary_text = tk.Text(
            notebook,
            wrap="word",
            font=("Consolas", 10),
        )
        notebook.add(
            self.summary_text,
            text="Resultado",
        )

        self.candidates = ttk.Treeview(
            notebook,
            columns=(
                "status",
                "marketplace",
                "match",
                "image",
                "title",
                "url",
            ),
            show="headings",
        )
        self.candidates.heading(
            "status",
            text="Status",
        )
        self.candidates.heading(
            "marketplace",
            text="Marketplace",
        )
        self.candidates.heading(
            "match",
            text="Match",
        )
        self.candidates.heading(
            "image",
            text="Imagem",
        )
        self.candidates.heading(
            "title",
            text="Produto",
        )
        self.candidates.heading(
            "url",
            text="URL",
        )

        self.candidates.column(
            "status",
            width=130,
            stretch=False,
        )
        self.candidates.column(
            "marketplace",
            width=130,
            stretch=False,
        )
        self.candidates.column(
            "match",
            width=80,
            stretch=False,
        )
        self.candidates.column(
            "image",
            width=80,
            stretch=False,
        )
        self.candidates.column(
            "title",
            width=330,
        )
        self.candidates.column(
            "url",
            width=350,
        )
        self.candidates.bind(
            "<Double-1>",
            self._open_selected_candidate,
        )
        notebook.add(
            self.candidates,
            text="Candidatos visuais",
        )

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(10, 0))

        ttk.Label(
            bottom,
            text=(
                "Durante o teste uma janela do Chrome pode abrir. "
                "Não faça login: deixe o AGCN executar a pesquisa."
            ),
        ).pack(side="left")

        ttk.Button(
            bottom,
            text="Abrir candidato selecionado",
            command=self._open_selected_candidate,
        ).pack(side="right")

    def _start_analysis(self):
        url = self.url_var.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showerror(
                "Link inválido",
                "Cole um link válido do produto do TikTok.",
            )
            return

        self.button.configure(state="disabled")
        self.status_var.set(
            "Analisando... aguarde o Google Lens abrir e concluir."
        )
        self.summary_text.delete("1.0", "end")
        for item in self.candidates.get_children():
            self.candidates.delete(item)

        thread = threading.Thread(
            target=self._worker,
            args=(url,),
            daemon=True,
        )
        thread.start()

    def _worker(self, url: str):
        try:
            engine = ProductResearchEngineV054()

            # No teste Windows queremos enxergar o que o Lens está fazendo.
            engine.enrichment.lens.headless = False
            self.engine = engine

            result = engine.analyze(url)
            self.events.put(("success", result))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _drain_events(self):
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "success":
                    self._show_result(payload)
                else:
                    self.button.configure(state="normal")
                    self.status_var.set("Falha no teste.")
                    messagebox.showerror(
                        "Erro",
                        payload,
                    )
        except queue.Empty:
            pass

        self.after(100, self._drain_events)

    def _show_result(self, result: dict):
        self.last_result = result
        self.button.configure(state="normal")

        values = result.get("values") or {}
        summary = result.get("research_summary") or {}
        enrichment = summary.get("enrichment") or {}
        discovery = enrichment.get("discovery") or {}
        candidates = enrichment.get("candidate_matches") or []
        specs = summary.get("technical_specs") or []

        self.status_var.set(
            "Concluído. "
            + str(len(candidates))
            + " candidato(s) encontrado(s); "
            + str(enrichment.get("confirmed_match_count") or 0)
            + " confirmado(s)."
        )

        lines = [
            "IDENTIDADE TIKTOK",
            "=================",
            "Nome: " + str(values.get("name") or ""),
            "Marca: " + str(values.get("brand") or ""),
            "Modelo: " + str(values.get("model") or ""),
            "Categoria: " + str(values.get("category") or ""),
            "Imagem: " + str(values.get("image_url") or ""),
            "",
            "GOOGLE LENS",
            "===========",
            "Ativado: " + str(discovery.get("lens_enabled")),
            "Usado: " + str(discovery.get("lens_used")),
            "Resultados: " + str(discovery.get("lens_result_count") or 0),
            "Marketplaces: " + str(discovery.get("lens_marketplace_count") or 0),
            "",
            "ESPECIFICAÇÕES CONFIRMADAS",
            "==========================",
        ]

        if specs:
            for spec in specs:
                lines.append(
                    "- "
                    + str(spec.get("name"))
                    + ": "
                    + str(spec.get("value"))
                    + " | fontes="
                    + str(spec.get("source_count") or 1)
                )
        else:
            lines.append(
                "Nenhuma especificação confirmada nesta tentativa."
            )

        lines.extend([
            "",
            "OBSERVAÇÕES",
            "===========",
        ])
        for note in summary.get("notes") or []:
            lines.append("- " + str(note))

        self.summary_text.insert(
            "1.0",
            "\n".join(lines),
        )

        for candidate in candidates:
            image_match = candidate.get("image_match") or {}
            image_score = image_match.get("score")

            status = (
                "CONFIRMADO"
                if candidate.get("verification") == "confirmed"
                else "CONFIRMAR"
            )
            match = round(
                float(candidate.get("match_score") or 0) * 100
            )
            image_percent = (
                str(round(float(image_score) * 100)) + "%"
                if image_score is not None
                else "-"
            )

            self.candidates.insert(
                "",
                "end",
                values=(
                    status,
                    candidate.get("marketplace")
                    or candidate.get("host")
                    or "",
                    str(match) + "%",
                    image_percent,
                    candidate.get("title") or "",
                    candidate.get("url") or "",
                ),
            )

    def _open_selected_candidate(self, _event=None):
        selection = self.candidates.selection()
        if not selection:
            return

        values = self.candidates.item(
            selection[0],
            "values",
        )
        if len(values) >= 6 and values[5]:
            webbrowser.open(values[5])


def self_test() -> int:
    from core.product_enrichment import MarketplaceEnrichmentEngine
    from core.visual_product_discovery import (
        GoogleLensDiscovery,
        VisualImageMatcher,
    )

    engine = MarketplaceEnrichmentEngine()
    assert engine is not None
    assert GoogleLensDiscovery.available()
    assert VisualImageMatcher() is not None

    print("AGCN_PRODUCT_IDENTITY_SELF_TEST_OK")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    app = ProductIdentityTester()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
