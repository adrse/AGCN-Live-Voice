from __future__ import annotations

import re
import unicodedata


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fold(value) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


class ProductKnowledge:
    """Base factual do produto para o Presenter.

    Não cria fatos. Ela organiza os campos preenchidos pelo usuário e consegue
    localizar respostas em descrição/especificações quando o comentário não
    cabe em um campo fixo.
    """

    FIELD_LABELS = {
        "name": "nome",
        "brand": "marca",
        "model": "modelo",
        "category": "categoria",
        "description": "descrição",
        "key_benefits": "principais benefícios",
        "problems_solved": "problemas que resolve",
        "differentials": "diferenciais",
        "included_items": "itens inclusos",
        "compatibility": "compatibilidade",
        "size_info": "tamanho e medidas",
        "battery_info": "bateria e autonomia",
        "usage_info": "modo de uso",
        "warranty": "garantia",
        "limitations": "limitações",
        "additional_info": "informações adicionais",
        "shipping_info": "frete e entrega",
        "coupon": "cupom",
        "live_offer_text": "oferta da LIVE",
    }

    TOPIC_FIELDS = {
        "brand": ["brand"],
        "model": ["model"],
        "category": ["category"],
        "availability": ["stock"],
        "shipping": ["shipping_info"],
        "warranty": ["warranty"],
        "compatibility": ["compatibility", "additional_info"],
        "included_items": ["included_items", "additional_info"],
        "size": ["size_info", "additional_info"],
        "battery": ["battery_info", "additional_info"],
        "usage": ["usage_info", "description", "additional_info"],
        "benefits": ["key_benefits", "differentials"],
        "problems_solved": ["problems_solved"],
        "differentials": ["differentials"],
    }

    QUESTION_HINTS = {
        "potencia": ("Potência", ("potencia", "watts", "watt", " w")),
        "voltagem": ("Voltagem", ("voltagem", "tensao", "110", "127", "220", "bivolt")),
        "capacidade": ("Capacidade", ("capacidade", "litro", "litros", "ml")),
        "material": ("Material", ("material", "feito de", "fabricado em")),
        "cor": ("Cor", ("cor", "cores", "preto", "branco", "inox")),
        "temperatura": ("Temperatura", ("temperatura", "graus", "°")),
        "peso": ("Peso", ("peso", "kg", "quilo")),
        "dimensoes": ("Dimensões", ("dimensao", "dimensoes", "altura", "largura", "comprimento", "cm")),
        "frequencia": ("Frequência", ("frequencia", "hz")),
        "tomada": ("Tomada / pino", ("tomada", "pino", "plugue")),
        "controle": ("Controle", ("controle remoto", "controle")),
        "programas": ("Programas / funções", ("programa", "programas", "funcao", "funcoes", "modo")),
        "resistencia_agua": ("Resistência à água", ("agua", "molhar", "impermeavel", "atm", "ip67", "ip68")),
        "internet": ("Internet / conexão", ("internet", "wifi", "wi-fi", "4g", "5g", "chip", "sim card")),
    }

    def __init__(self, product: dict | None):
        self.product = dict(product or {})
        self.specs = self._parse_specs()
        self.search_chunks = self._build_chunks()

    def resolve(
        self,
        *,
        intent: str | None,
        topic: str | None,
        comment: str | None,
    ) -> dict:
        intent = clean(intent)
        topic = clean(topic)
        comment_text = clean(comment)

        if intent == "price" or topic == "price":
            return self._price_packet()

        # Campos fixos primeiro.
        fields = self.TOPIC_FIELDS.get(topic) or self.TOPIC_FIELDS.get(intent) or []
        packet = self._first_field(fields)
        if packet:
            return packet

        # Perguntas técnicas específicas.
        technical = self._technical_answer(comment_text)
        if technical:
            return technical

        # Pergunta genérica: tenta localizar a informação cadastrada mais
        # relacionada ao texto do espectador.
        if intent in {"direct_question", "technical_question", "safety_or_critical"}:
            contextual = self._contextual_answer(comment_text)
            if contextual:
                return contextual

        return {
            "found": False,
            "value": None,
            "label": None,
            "field": None,
            "items": [],
        }

    def get(self, field: str):
        value = self.product.get(field)
        return value if value not in (None, "", [], {}) else None

    def _price_packet(self) -> dict:
        current = self.product.get("current_price")
        regular = self.product.get("regular_price")
        discount = self.product.get("discount")
        if current in (None, "") and regular in (None, ""):
            return self._empty()

        return {
            "found": True,
            "value": {
                "current_price": current,
                "regular_price": regular,
                "discount": discount,
            },
            "label": "preço",
            "field": "price",
        }

    def _first_field(self, fields: list[str]) -> dict | None:
        for field in fields:
            value = self.product.get(field)
            if value in (None, "", [], {}):
                continue
            items = self.entries(value)
            return {
                "found": True,
                "value": value,
                "items": items,
                "label": self.FIELD_LABELS.get(field, field),
                "field": field,
            }
        return None

    @staticmethod
    def entries(value) -> list[str]:
        if value in (None, "", [], {}):
            return []

        if isinstance(value, (list, tuple, set)):
            raw = [clean(x) for x in value]
        else:
            raw = [
                clean(x)
                for x in re.split(r"[\n;|]+", str(value or ""))
            ]

        out = []
        seen = set()
        for item in raw:
            if not item:
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _parse_specs(self) -> dict[str, str]:
        specs = {}
        sources = [
            self.product.get("additional_info"),
            self.product.get("compatibility"),
            self.product.get("size_info"),
            self.product.get("battery_info"),
        ]

        for source in sources:
            raw_text = str(source or "")
            if not clean(raw_text):
                continue

            raw_text = re.sub(
                r"^especifica(?:c|ç)(?:ao|ões|oes) tecnicas?\s*:\s*",
                "",
                raw_text,
                flags=re.I,
            )

            for part in re.split(r"[;\n|]+", raw_text):
                part = clean(part)
                if not part or ":" not in part:
                    continue
                label, value = part.split(":", 1)
                label = clean(label).strip(" -•")
                value = clean(value).strip(" -•")
                if label and value and len(label) <= 80:
                    specs[fold(label)] = value

        # Campos estruturados também entram como aliases de especificação.
        aliases = {
            "marca": "brand",
            "modelo": "model",
            "categoria": "category",
            "garantia": "warranty",
            "tamanho": "size_info",
            "medidas": "size_info",
            "bateria": "battery_info",
            "compatibilidade": "compatibility",
        }
        for label, field in aliases.items():
            value = self.product.get(field)
            if value not in (None, "", [], {}):
                specs.setdefault(label, clean(value))

        return specs

    def _technical_answer(self, comment: str) -> dict | None:
        question = fold(comment)
        if not question:
            return None

        for _, (display, hints) in self.QUESTION_HINTS.items():
            if not any(fold(hint) in question for hint in hints):
                continue

            # Procura primeiro um rótulo explícito nas especificações.
            for label, value in self.specs.items():
                if any(fold(hint).strip() in label for hint in hints):
                    return {
                        "found": True,
                        "value": value,
                        "label": display,
                        "field": "additional_info",
                    }

            # Depois procura a informação dentro dos campos textuais.
            snippet = self._find_snippet(hints)
            if snippet:
                return {
                    "found": True,
                    "value": snippet,
                    "label": display,
                    "field": "context",
                }

        return None

    def _contextual_answer(self, comment: str) -> dict | None:
        q_tokens = self._tokens(comment)
        if not q_tokens:
            return None

        best = None
        best_score = 0

        for chunk in self.search_chunks:
            chunk_tokens = self._tokens(chunk["text"])
            overlap = len(q_tokens & chunk_tokens)
            if overlap <= 0:
                continue

            score = overlap / max(1, min(len(q_tokens), 6))
            if chunk["field"] in {"additional_info", "description"}:
                score += 0.08

            if score > best_score:
                best_score = score
                best = chunk

        if best and best_score >= 0.18:
            return {
                "found": True,
                "value": best["text"],
                "label": best["label"],
                "field": best["field"],
            }

        return None

    def _find_snippet(self, hints: tuple[str, ...]) -> str | None:
        folded_hints = [fold(x).strip() for x in hints]

        for chunk in self.search_chunks:
            text_fold = fold(chunk["text"])
            if any(h and h in text_fold for h in folded_hints):
                return chunk["text"]

        return None

    def _build_chunks(self) -> list[dict]:
        chunks = []
        fields = [
            "brand",
            "model",
            "category",
            "description",
            "key_benefits",
            "problems_solved",
            "differentials",
            "included_items",
            "compatibility",
            "size_info",
            "battery_info",
            "usage_info",
            "warranty",
            "limitations",
            "additional_info",
            "shipping_info",
        ]

        for field in fields:
            value = self.product.get(field)
            raw_text = str(value or "")
            text = clean(raw_text)
            if not text:
                continue

            # Divide os itens cadastrados separadamente sem perder quebras
            # de linha usadas pela interface.
            parts = [
                clean(x)
                for x in re.split(r"[;\n|]+", raw_text)
                if clean(x)
            ] or [text]

            for part in parts:
                chunks.append({
                    "field": field,
                    "label": self.FIELD_LABELS.get(field, field),
                    "text": part,
                })

        for label, value in self.specs.items():
            chunks.append({
                "field": "additional_info",
                "label": label,
                "text": f"{label}: {value}",
            })

        return chunks

    @staticmethod
    def _tokens(text: str) -> set[str]:
        raw = re.findall(r"[a-zA-ZÀ-ÿ0-9]+", fold(text))
        stop = {
            "qual", "quanto", "quantos", "quantas", "como", "isso", "esse",
            "essa", "ele", "ela", "tem", "com", "sem", "para", "pra", "por",
            "que", "uma", "uns", "das", "dos", "de", "do", "da", "e", "o", "a",
            "me", "fala", "diz", "sabe", "produto",
        }
        return {x for x in raw if len(x) >= 2 and x not in stop}

    @staticmethod
    def _empty() -> dict:
        return {
            "found": False,
            "value": None,
            "label": None,
            "field": None,
        }
