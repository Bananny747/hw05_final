from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


class Post(models.Model):
    text = models.TextField(
        'Текст поста',
        help_text='Напишите что-то, за что не будет стыдно'
    )
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='post',
        verbose_name='Автор',
    )
    group = models.ForeignKey(
        'Group',
        blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='post',
        verbose_name='Группа'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ('-pub_date',)

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    text = models.TextField(
        'Текст комменатрия',
        help_text='Оставьте свое искреннее мнение, но помните: его увидят все'
    )
    created = models.DateTimeField(
        'Дата публикации комментария',
        auto_now_add=True
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор',
    )

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return self.text[:15]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор',
    )


class Group(models.Model):
    title = models.CharField('Имя группы', max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField('Описание')

    def __str__(self):
        return self.title
