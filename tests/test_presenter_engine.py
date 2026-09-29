import unittest

from core.presenter_engine import PresenterEngine


PRODUCT = {
    "name": "SmartBand X",
    "description": "Compatibilidade com produtos antigos.",
    "description_points": [
        "A bateria dura até 6 dias",
        "Monitora passos, sono e frequência cardíaca",
    ],
    "regular_price": 199.90,
    "current_price": 149.90,
    "discount": 25,
    "additional_info": (
        "Possui garantia de 1 ano. "
        "Compatível com Android e iPhone."
    ),
}


class PresenterBehaviorTests(unittest.TestCase):
    def test_price_reply_is_natural_and_does_not_expose_internal_storage(self):
        engine = PresenterEngine(PRODUCT)
        reply = engine.build_response("Maria", "quanto custa?", "price")

        self.assertIn("Maria", reply)
        self.assertIn("149,90", reply)
        self.assertNotIn("cadastr", reply.casefold())
        self.assertNotIn("base de dados", reply.casefold())

    def test_direct_question_finds_relevant_product_fact(self):
        engine = PresenterEngine(PRODUCT)
        reply = engine.build_response(
            "João",
            "quanto tempo dura a bateria?",
            "direct_question",
        )

        self.assertIn("6 dias", reply)
        self.assertNotIn("cadastr", reply.casefold())

    def test_unknown_question_is_silently_ignored(self):
        engine = PresenterEngine(PRODUCT)

        reply = engine.build_response(
            "Ana",
            "ele tem gps integrado?",
            "direct_question",
        )
        queued = engine.enqueue_comment(
            "Ana",
            "ele tem gps integrado?",
        )

        self.assertIsNone(reply)
        self.assertIsNone(queued)
        self.assertEqual(engine.queue_snapshot(), [])

    def test_known_guarantee_reply_is_short_and_informal(self):
        engine = PresenterEngine(PRODUCT)
        reply = engine.build_response(
            "Maria",
            "tem garantia?",
            "direct_question",
        )

        self.assertIn("Maria", reply)
        self.assertIn("tem garantia de 1 ano", reply.casefold())
        self.assertLess(len(reply), 120)

    def test_three_reactive_answers_force_thirty_seconds_of_product_talk(self):
        engine = PresenterEngine(PRODUCT)
        base = 1000.0

        for index in range(engine.MAX_REACTIVE_BURST):
            item = {
                "type": "reactive",
                "speech": f"resposta {index}",
            }
            engine.mark_spoken(
                item,
                now=base + index,
                speech_until=base + index + 5,
            )

        expected_start = base + engine.MAX_REACTIVE_BURST - 1 + 5
        self.assertFalse(engine.can_take_reactive(expected_start + 1))
        self.assertGreaterEqual(
            engine.seconds_until_reactive(expected_start + 1),
            28,
        )
        self.assertTrue(
            engine.can_take_reactive(
                expected_start + engine.FORCED_SALES_SECONDS + 1
            )
        )

    def test_proactive_speech_stays_on_product(self):
        engine = PresenterEngine(PRODUCT)
        item = engine.build_proactive(now=1000.0)

        self.assertEqual(item["type"], "proactive")
        self.assertIn("SmartBand X", item["speech"])
        self.assertIn("6 dias", item["speech"])
        self.assertNotIn("monitora passos", item["speech"].casefold())
        self.assertNotIn("cadastr", item["speech"].casefold())


if __name__ == "__main__":
    unittest.main()
