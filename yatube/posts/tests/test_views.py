import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django import forms
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим записи в БД для проверки доступности адресов
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.wrong_group = Group.objects.create(
            title='Тестовая неправильная группа',
            slug='test-slug-wrong',
            description='Тестовое описание неправильной группы',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(PostsPagesTests.user)
        cache.clear()

    def test_cache(self):
        """Тест кэша, контент останется в ответе после удаления из базы."""
        cache_post = Post.objects.create(
            author=PostsPagesTests.user,
            text='Пост для кэша',
            group=None,
            image=None,
        )
        response = self.guest_client.get(reverse('posts:index'))
        self.assertIn(cache_post, response.context['page_obj'])
        Post.objects.get(id=cache_post.id).delete()
        # Повторное обращение к серверу после удаления
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertIn(bytes(cache_post.text, 'utf-8'), response.content)
        # Очищаем кэшё
        cache.clear()
        response2 = self.client.get(reverse('posts:index'))
        self.assertFalse(cache_post in response2.context['page_obj'])

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "reverse(name): имя_html_шаблона"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse(
                'posts:group_post',
                kwargs={'slug': PostsPagesTests.group.slug})
             ):
            'posts/group_list.html',
            (reverse(
                'posts:profile',
                kwargs={'username': PostsPagesTests.user.username})
             ):
            'posts/profile.html',
            (reverse(
                'posts:post_detail',
                kwargs={'post_id': PostsPagesTests.post.id})
             ):
            'posts/post_detail.html',
            (reverse(
                'posts:post_edit',
                kwargs={'post_id': PostsPagesTests.post.id})
             ):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        # Проверяем, что при обращении к name вызывается соответствующий шаблон
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.client.get(reverse('posts:index'))
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        image_path = 'posts/small.gif'
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author, PostsPagesTests.user)
        self.assertEqual(first_object.group, PostsPagesTests.group)
        self.assertEqual(first_object.image, image_path)

    def test_post_create_edit_page_show_correct_context(self):
        """Шаблоны post_create, _edit сформированы с правильным контекстом."""
        urls = (
            ('posts:post_create', None),
            ('posts:post_edit', [PostsPagesTests.post.id]),
        )
        for url, args in urls:
            response = self.authorized_client.get(reverse(url, args=args))
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
                'image': forms.fields.ImageField,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон task_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': PostsPagesTests.post.id})))
        self.assertEqual(response.context.get('post').text, 'Тестовый пост')
        self.assertEqual(
            response.context.get('post').author, PostsPagesTests.user
        )
        self.assertEqual(response.context.get('post').image, 'posts/small.gif')

    def test_post_exists_on_index_author_group_pages(self):
        """Новый пост отображается на нужных страницах."""
        urls = (
            ('posts:index', None),
            ('posts:group_post', [PostsPagesTests.group.slug]),
            ('posts:profile', [PostsPagesTests.user.username]),
        )
        for url, args in urls:
            response = self.client.get(reverse(url, args=args))
            self.assertTrue(
                PostsPagesTests.post in response.context['page_obj']
            )
        response = self.client.get(reverse(
            'posts:group_post',
            kwargs={'slug': PostsPagesTests.wrong_group.slug})
        )
        self.assertFalse(
            PostsPagesTests.post in response.context['page_obj']
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим записи в БД для проверки доступности адресов
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        posts = [
            Post(
                author=cls.user,
                group=cls.group,
                text=f'Тестовый пост {n}') for n in range(1, 14)
        ]
        Post.objects.bulk_create(posts)
        cls.urls = (
            ('posts:index', None),
            ('posts:group_post', [cls.group.slug]),
            ('posts:profile', [cls.user.username]),
        )
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """Проверка количества постов на 1 странице."""
        for url, args in self.urls:
            response = self.client.get(reverse(url, args=args))
            # Проверка: количество постов на первой странице равно 10.
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """Проверка количества постов на 2 странице."""
        for url, args in self.urls:
            # Проверка: на второй странице должно быть три поста.
            response = self.client.get(reverse(url, args=args) + '?page=2')
            self.assertEqual(len(response.context['page_obj']), 3)
