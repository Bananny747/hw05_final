from django.test import TestCase, Client
from django.core.cache import cache


class PostsURLTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_404_errors_correct_template(self):
        """Ошибка 404 использует соответствующий шаблон."""
        response = Client().get('/unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')
