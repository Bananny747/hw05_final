from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from http import HTTPStatus
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим записи в БД для проверки доступности адресов
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.post2 = Post.objects.create(
            author=cls.user2,
            text='Тестовый пост2',
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(PostsURLTests.user)
        cache.clear()

    def test_url_exists_for_all(self):
        """Страницы доступны любому пользователю."""
        url_for_all = [
            '/',
            f'/group/{PostsURLTests.group.slug}/',
            f'/profile/{PostsURLTests.user.username}/',
            f'/posts/{PostsURLTests.post.id}/',
        ]
        for url in url_for_all:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_redirect_not_author(self):
        """Не автор пытается изменить пост."""
        response = self.authorized_client.get(
            f'/posts/{PostsURLTests.post2.id}/edit/',
            follow=True
        )
        self.assertRedirects(
            response,
            f'/posts/{PostsURLTests.post2.id}/'
        )

    def test_create_url_redirect_anonymous_on_login(self):
        """Незарегистрированный пользователь пытается создать пост."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    def test_unexisting_page(self):
        """Несуществующая страница."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Шаблоны по адресам
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostsURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostsURLTests.user.username}/': 'posts/profile.html',
            f'/posts/{PostsURLTests.post.id}/': 'posts/post_detail.html',
            f'/posts/{PostsURLTests.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
