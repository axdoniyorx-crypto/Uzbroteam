from aiogram import Router

from . import user, tiktok, youtube, spotify, admin, twitter, instagram, soundcloud, pinterest, threads, language_handler, admin_extended, music_search, shazam

router = Router(name=__name__)

router.include_routers(
    language_handler.router,
    user.router,
    tiktok.router,
    youtube.router,
    spotify.router,
    admin_extended.router,
    admin.router,
    twitter.router,
    instagram.router,
    threads.router,
    soundcloud.router,
    pinterest.router,
    shazam.router,
    music_search.router,
)

__all__ = [
    router
]
