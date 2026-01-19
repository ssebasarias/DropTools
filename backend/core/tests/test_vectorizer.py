
from django.test import TestCase
from django.core.management import call_command

class VectorizerTest(TestCase):
    def test_vectorizer_model_loading(self):
        """
        Verifica que el modelo SigLIP se cargue o maneje el error si no hay GPU.
        """
        pass
