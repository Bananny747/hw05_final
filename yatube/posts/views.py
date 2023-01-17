from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow
from django.views.decorators.cache import cache_page


POSTS_ON_PAGE = 10


def custom_paginator(request, post_list):
    paginator = Paginator(post_list, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


@cache_page(20, key_prefix='index_page')
def index(request):
    """Функция-обработчик главной страницы."""
    template = 'posts/index.html'
    post_list = Post.objects.all()
    context = {
        'page_obj': custom_paginator(request, post_list),
    }
    return render(request, template, context)


def group_post(request, slug):
    """Функция-обработчик страницы запрощенной группы."""
    group = get_object_or_404(Group, slug=slug)
    post_list = group.post.all()
    context = {
        'page_obj': custom_paginator(request, post_list),
        'group': group,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Здесь код запроса к модели и создание словаря контекста."""
    author = get_object_or_404(User, username=username)
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(
            user=request.user, author=author
        ).exists()
    )
    post_list = author.post.all()
    context = {
        'page_obj': custom_paginator(request, post_list),
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Здесь код запроса к модели и создание словаря контекста."""
    post = get_object_or_404(Post, id=post_id)
    comment_list = post.comments.all()
    form = CommentForm(
        request.POST or None,
    )
    context = {
        'post': post,
        'CommentForm': form,
        'comment_list': comment_list,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def add_comment(request, post_id):
    # Получите пост и сохраните его в переменную post.
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect('posts:profile', username=new_post.author)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author.id != request.user.id:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    context = {
        'form': form,
        'is_edit': True,
        'post_id': post_id,
    }
    # понял, что проверка типа запроса не обязательна, т.к. если валидна,
    # значит и был запрос пост, но пока хочу оставить, чтобы потом вспомнить
    # эту логику
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id=post_id)
        return render(request, 'posts/create_post.html', context)
    return render(request, 'posts/create_post.html', context)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    context = {
        'page_obj': custom_paginator(request, post_list),
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    # Подписаться на автора
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:index')


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    follow = get_object_or_404(
        Follow,
        user=request.user,
        author__username=username)
    follow.delete()
    return redirect('posts:profile', username)
