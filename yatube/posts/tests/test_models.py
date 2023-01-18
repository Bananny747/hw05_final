from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Post, Group

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        group = PostModelTest.group
        post = PostModelTest.post
        expected_group_value = group.title
        expected_post_value = post.text[:15]
        self.assertEqual(expected_group_value, str(group))
        self.assertEqual(expected_post_value, str(post))

    def test_models_have_correct_object_names(self):
        """Проверяем, что у модели Post корректно работает
        verbose_name и help_text."""
        post = PostModelTest.post
        self.assertEqual(
            post._meta.get_field('text').verbose_name,
            'Текст поста')
        self.assertEqual(
            post._meta.get_field('text').help_text,
            'Напишите что-то, за что не будет стыдно')
        self.assertEqual(post._meta.get_field('group').verbose_name, 'Группа')
