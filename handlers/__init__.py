from aiogram import Router

from . import user, tiktok, youtube, spotify, admin, twitter, instagram, soundcloud, pinterest, threads, language_handler, admin_extended

router = Router(name=__name__)

router.include_routers(
    language_handler.router,
    user.router,
    tiktok.router,
    youtube.router,
    spotify.router,
    admin.router,
    admin_extended.router,
    twitter.router,
    instagram.router,
    threads.router,
    soundcloud.router,
    pinterest.router,
)

__all__ = [
    router
]
