"""AI yordamchisi: model o'chirilganda ham ishlab ketishi.

Bepul provayderlar model nomlarini tez-tez o'zgartiradi. Bitta nomga
bog'lanib qolinsa, model o'chirilgan kuni AI yordamchi butunlay ishlamay
qoladi va foydalanuvchi tushunarsiz 404 xatosini ko'radi.
"""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.core import ai

GROQ_KEY = "gsk_sinov_kalit"


@override_settings(AI_API_KEY=GROQ_KEY, AI_PROVIDER="groq", AI_MODEL="")
class ModelFallbackTests(SimpleTestCase):
    def setUp(self):
        ai._working_model.clear()

    def test_ochirilgan_model_keyingisiga_otadi(self):
        tried = []

        def fake_send(messages, model, provider):
            tried.append(model)
            if len(tried) == 1:
                raise ai.AIError(
                    f"AI xizmati xatosi (404): The model `{model}` does not exist", status=404
                )
            return "javob"

        with patch.object(ai, "_send", side_effect=fake_send):
            answer = ai.chat([{"role": "user", "content": "salom"}])

        self.assertEqual(answer, "javob")
        self.assertEqual(len(tried), 2)

    def test_ishlagan_model_eslab_qolinadi(self):
        """Ikkinchi so'rovda o'chirilgan modelni qaytadan sinamaslik kerak."""
        tried = []

        def fake_send(messages, model, provider):
            tried.append(model)
            if model == ai.MODEL_CANDIDATES["groq"][0]:
                raise ai.AIError("does not exist", status=404)
            return "javob"

        with patch.object(ai, "_send", side_effect=fake_send):
            ai.chat([{"role": "user", "content": "salom"}])
            first_round = len(tried)
            ai.chat([{"role": "user", "content": "yana"}])

        # Ikkinchi so'rovda faqat bitta urinish bo'lishi kerak.
        self.assertEqual(len(tried) - first_round, 1)

    def test_kalit_xatosida_boshqa_model_sinalmaydi(self):
        """401 - kalit muammosi. Hamma modelni sinash behuda vaqt."""
        tried = []

        def fake_send(messages, model, provider):
            tried.append(model)
            raise ai.AIError("AI xizmati xatosi (401): Invalid API Key", status=401)

        with patch.object(ai, "_send", side_effect=fake_send):
            with self.assertRaises(ai.AIError):
                ai.chat([{"role": "user", "content": "salom"}])

        self.assertEqual(len(tried), 1)

    def test_hamma_model_ochirilgan_bolsa_royxat_korsatiladi(self):
        def fake_send(messages, model, provider):
            raise ai.AIError("does not exist", status=404)

        with patch.object(ai, "_send", side_effect=fake_send), patch.object(
            ai, "available_models", return_value=["llama-3.1-8b-instant", "qwen/qwen3-32b"]
        ):
            with self.assertRaises(ai.AIError) as caught:
                ai.chat([{"role": "user", "content": "salom"}])

        message = str(caught.exception)
        self.assertIn("llama-3.1-8b-instant", message)
        self.assertIn("AI_MODEL", message)

    @override_settings(AI_MODEL="men-tanlagan-model")
    def test_qolda_tanlangan_model_ozgartirilmaydi(self):
        tried = []

        def fake_send(messages, model, provider):
            tried.append(model)
            raise ai.AIError("does not exist", status=404)

        with patch.object(ai, "_send", side_effect=fake_send), patch.object(
            ai, "available_models", return_value=[]
        ):
            with self.assertRaises(ai.AIError):
                ai.chat([{"role": "user", "content": "salom"}])

        self.assertEqual(tried, ["men-tanlagan-model"])


class MissingModelDetectionTests(SimpleTestCase):
    def test_matn_bo_yicha_aniqlanadi(self):
        self.assertTrue(ai._is_missing_model(ai.AIError("model does not exist", status=404)))
        self.assertTrue(ai._is_missing_model(ai.AIError("has been decommissioned", status=400)))
        self.assertFalse(ai._is_missing_model(ai.AIError("Invalid API Key", status=401)))
        self.assertFalse(ai._is_missing_model(ai.AIError("rate limit", status=429)))
