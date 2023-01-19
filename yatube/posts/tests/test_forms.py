import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache

from ..models import Post, Group, Follow
from ..forms import PostForm


User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateEditFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.old_group = Group.objects.create(
            title='Тестовая старая группа',
            slug='test_old_group',
            description='Описание старой тестовой группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост ожидает редактирования',
            group=cls.old_group,
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Описание тестовой группы',
        )
        # Создаем форму, если нужна проверка атрибутов
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostCreateEditFormTests.user)
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        cache.clear()

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': PostCreateEditFormTests.group.id,
            'image': self.uploaded,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        new_post = Post.objects.filter(text='Тестовый текст')[0]
        image_path = 'posts/small.gif'
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:profile', args=[PostCreateEditFormTests.user.username]))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # Проверяем, содержание нового поста
        self.assertEqual(new_post.author, PostCreateEditFormTests.user)
        self.assertEqual(new_post.group, PostCreateEditFormTests.group)
        self.assertEqual(new_post.image, image_path)

    def test_comment_redirect_anonymous_on_login(self):
        """Незарегистрированный пользователь пытается комментировать пост."""
        form_data = {
            'text': 'Тестовый текст комментария',
        }
        # Отправляем POST-запрос
        response = self.client.post(
            reverse('posts:add_comment',
                    args=[PostCreateEditFormTests.post.id]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            '/auth/login/?next=/posts/'
            f'{PostCreateEditFormTests.post.id}/comment/'
        )

    def test_add_comment(self):
        """Валидная форма добавляет комментарий."""
        form_data = {
            'text': 'Тестовый текст комментария',
        }
        # Отправляем POST-запрос
        self.authorized_client.post(
            reverse('posts:add_comment',
                    args=[PostCreateEditFormTests.post.id]),
            data=form_data,
            follow=True,
        )
        # Проверяем, появился ли комментарий
        self.assertEqual(
            Post.objects.get(pk=PostCreateEditFormTests.post.pk).comments.get(
                text=form_data['text']).text,
            form_data['text']
        )

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        form_data = {
            'text': 'Тестовый пост дождался редактирования',
            'group': PostCreateEditFormTests.group.id,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=[PostCreateEditFormTests.post.id]),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=[PostCreateEditFormTests.post.id]))
        # Проверяем, изменился ли пост
        self.assertEqual(
            Post.objects.get(pk=PostCreateEditFormTests.post.pk).text,
            form_data['text']
        )
        self.assertEqual(
            Post.objects.get(pk=PostCreateEditFormTests.post.pk).group.id,
            form_data['group']
        )
        # Проверяем, что пост изчез из старой группы
        old_group_response = self.authorized_client.get(
            reverse('posts:group_post',
                    args=[PostCreateEditFormTests.old_group.slug])
        )
        self.assertEqual(
            old_group_response.context['page_obj'].paginator.count,
            0
        )

    def test_create_user(self):
        """Валидная форма создает запись нового пользователя."""
        # Подсчитаем количество записей в User
        users_count = User.objects.count()
        form_data = {
            'username': 'test_username',
            'password1': 'test_password',
            'password2': 'test_password',
        }
        # Отправляем POST-запрос
        self.client.post(
            reverse('users:signup'),
            data=form_data,
            follow=True
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(User.objects.count(), users_count + 1)


class FollowCreateEditTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Это автор
        cls.user = User.objects.create_user(username='auth')
        cls.user_follower = User.objects.create_user(username='user_follower')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        # еще один пользователь, третье лицо
        cls.third_person = User.objects.create_user(username='third_person')

    def setUp(self):
        # Создаем клиент подписчика
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(FollowCreateEditTests.user_follower)
        # Создаем клиент третьего лица
        self.authorized_client_for_third_person = Client()
        # Авторизуем пользователя
        self.authorized_client_for_third_person.force_login(
            FollowCreateEditTests.third_person)

    def test_authenticated_user_follow_unfollow(self):
        """Авторизованный пользователь подписывается
        на других пользователей."""
        self.authorized_client.post(
            reverse('posts:profile_follow',
                    args=[FollowCreateEditTests.user]),
            follow=True
        )
        self.assertTrue(Follow.objects.filter(
            user=FollowCreateEditTests.user_follower).exists())

    def test_authenticated_user_follow_unfollow(self):
        """Авторизованный пользователь может удалять из подписок."""
        Follow.objects.create(
            user=FollowCreateEditTests.user_follower,
            author=FollowCreateEditTests.user
        )
        self.assertTrue(Follow.objects.filter(
            user=FollowCreateEditTests.user_follower).exists())
        # Проверяем отписку
        self.authorized_client.post(
            reverse('posts:profile_unfollow',
                    args=[FollowCreateEditTests.user]),
            follow=True
        )
        self.assertFalse(Follow.objects.filter(
            user=FollowCreateEditTests.user_follower).exists())

    def test_new_post_arise_in_follow_index(self):
        """Новая запись пользователя появляется в ленте тех, кто на него
        подписан и не появляется в ленте тех, кто не подписан."""
        self.authorized_client.post(
            reverse('posts:profile_follow',
                    args=[FollowCreateEditTests.user]),
            follow=True
        )
        new_post = Post.objects.create(
            author=FollowCreateEditTests.user,
            text='Тестовый пост',
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertTrue(
            new_post in response.context['page_obj']
        )
        # Пост не появился в ленте третьего лица
        response = self.authorized_client_for_third_person.get(
            reverse('posts:follow_index'))
        self.assertFalse(
            new_post in response.context['page_obj']
        )
