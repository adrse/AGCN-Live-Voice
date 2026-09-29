from __future__ import annotations

import re


def clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


class CommentIntelligence:
    """Classifica comentários comerciais e identifica o assunto principal."""

    INTENT_PRIORITY = {
        "safety_or_critical": 100,
        "buying_intent": 98,
        "price": 96,
        "objection": 94,
        "availability": 92,
        "compatibility": 91,
        "technical_question": 90,
        "shipping": 89,
        "coupon": 89,
        "warranty": 88,
        "brand": 86,
        "included_items": 85,
        "size": 84,
        "battery": 84,
        "benefits": 84,
        "usage": 82,
        "direct_question": 80,
        "purchase_confirmation": 68,
        "engagement": 42,
    }

    LABELS = {
        "safety_or_critical": "Pergunta crítica",
        "buying_intent": "Intenção de compra",
        "price": "Preço",
        "objection": "Objeção",
        "availability": "Disponibilidade",
        "compatibility": "Compatibilidade",
        "technical_question": "Pergunta técnica",
        "shipping": "Frete / entrega",
        "coupon": "Cupom / desconto",
        "warranty": "Garantia",
        "brand": "Marca",
        "included_items": "Itens inclusos",
        "size": "Tamanho / medida",
        "battery": "Bateria",
        "benefits": "Benefícios",
        "usage": "Como usar",
        "direct_question": "Pergunta direta",
        "purchase_confirmation": "Compra confirmada",
        "engagement": "Engajamento",
    }

    def analyze(self, user: str, text: str) -> dict | None:
        original = clean(text)
        t = original.casefold()
        if not t:
            return None

        intent = None
        topic = None

        if any(k in t for k in (
            "voltagem", "bivolt", "110", "220", "pode molhar",
            "à prova d", "a prova d", "seguro", "queima", "forno"
        )):
            intent, topic = "safety_or_critical", "safety"

        elif any(k in t for k in (
            "eu quero", "quero comprar", "quero um", "vou comprar",
            "vou levar", "como compra", "como comprar", "manda o link",
            "cadê o link", "cade o link", "onde compra", "onde comprar",
            "coloquei no carrinho", "já tá no carrinho", "ja ta no carrinho"
        )):
            intent, topic = "buying_intent", "buying"

        # Bateria precisa vir antes de preço: "quanto dura a bateria?"
        # é autonomia, não pergunta de valor.
        elif any(k in t for k in (
            "bateria", "dura quanto", "quanto dura", "carrega",
            "carregamento", "autonomia"
        )):
            intent, topic = "battery", "battery"

        elif any(k in t for k in (
            "quanto", "preço", "preco", "valor", "custa", "por quanto"
        )):
            intent, topic = "price", "price"

        elif any(k in t for k in (
            "caro", "muito caro", "frete caro", "não vale", "nao vale",
            "achei caro", "tá caro", "ta caro"
        )):
            intent, topic = "objection", "objection"

        elif any(k in t for k in (
            "tem estoque", "disponível", "disponivel", "tem ainda",
            "ainda tem", "resta", "acabou"
        )):
            intent, topic = "availability", "availability"

        elif any(k in t for k in (
            "serve no", "serve para", "compatível", "compativel",
            "funciona no", "iphone", "android", "indução", "inducao"
        )):
            intent, topic = "compatibility", "compatibility"

        elif any(k in t for k in ("frete", "entrega", "chega", "envio")):
            intent, topic = "shipping", "shipping"

        elif any(k in t for k in (
            "cupom", "desconto", "tem promoção", "tem promocao",
            "tem oferta", "qual a oferta"
        )):
            intent, topic = "coupon", "coupon"

        elif any(k in t for k in ("garantia", "garantido")):
            intent, topic = "warranty", "warranty"

        elif any(k in t for k in ("qual a marca", "que marca", "marca dele", "marca é", "marca e")):
            intent, topic = "brand", "brand"

        elif any(k in t for k in (
            "qual o modelo", "qual modelo", "modelo dele", "modelo é",
            "modelo e", "que modelo"
        )):
            intent, topic = "technical_question", "model"

        elif any(k in t for k in (
            "qual a categoria", "que tipo de produto", "qual tipo"
        )):
            intent, topic = "technical_question", "category"

        elif any(k in t for k in (
            "potência", "potencia", "watts", "watt",
            "material", "feito de", "fabricado em",
            "qual a cor", "qual cor", "que cor", "cor disponível", "cor disponivel", "cores",
            "internet", "wi-fi", "wifi", "4g", "5g", "chip", "sim card",
            "temperatura", "graus",
            "peso", "quantos kg", "quantos quilos",
            "dimensões", "dimensoes", "comprimento",
            "controle remoto", "vem controle", "tem controle",
            "quantos programas", "quantas funções", "quantas funcoes",
            "frequência", "frequencia", "hz",
            "tipo de pino", "tomada"
        )):
            intent, topic = "technical_question", "technical"

        elif any(k in t for k in (
            "vem com", "acompanha", "acessórios", "acessorios",
            "o que vem", "quantas peças", "quantas pecas"
        )):
            intent, topic = "included_items", "included_items"

        elif any(k in t for k in (
            "tamanho", "medida", "quantos cm", "quantos litros",
            "litros", "altura", "largura"
        )):
            intent, topic = "size", "size"

        elif any(k in t for k in (
            "quais benefícios", "quais beneficios", "benefícios quais",
            "beneficios quais", "benefícios?", "beneficios?",
            "benefício", "beneficio", "vantagens", "vantagem",
            "o que ele tem de bom", "o que tem de bom",
            "qual o benefício", "qual o beneficio",
            "quais as vantagens", "qual vantagem", "vale a pena",
            "é bom", "e bom"
        )):
            intent, topic = "benefits", "benefits"

        elif any(k in t for k in (
            "como usa", "como usar", "funciona", "serve pra",
            "serve para quê", "serve para que"
        )):
            intent, topic = "usage", "usage"

        elif any(k in t for k in (
            "comprei", "finalizei", "peguei um", "já comprei", "ja comprei"
        )):
            intent, topic = "purchase_confirmation", "purchase"

        else:
            is_question = (
                "?" in original
                or any(
                    t.startswith(x)
                    for x in (
                        "tem ", "qual ", "quanto ", "como ", "pode ",
                        "vem ", "é ", "e ", "faz ", "serve "
                    )
                )
            )
            if is_question:
                intent, topic = "direct_question", "general"
            elif any(k in t for k in (
                "amei", "lindo", "gostei", "top", "perfeito",
                "maravilhoso", "bom demais", "oi", "olá", "ola",
                "bom dia", "boa tarde", "boa noite", "salve",
                "manda salve", "cheguei"
            )):
                intent, topic = "engagement", "engagement"

        if not intent:
            return None

        return {
            "user": clean(user),
            "comment": original,
            "intent": intent,
            "topic": topic,
            "label": self.LABELS[intent],
            "priority": self.INTENT_PRIORITY[intent],
        }
