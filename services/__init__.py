def __getattr__(name):
    if name == "download_queue":
        from services.download import queue as download_queue
        return download_queue
    elif name == "download_worker_cli":
        from services.download import worker_cli as download_worker_cli
        return download_worker_cli
    elif name == "inline_album_links":
        from services.inline import album_links as inline_album_links
        return inline_album_links
    elif name == "inline_service_icons":
        from services.inline import service_icons as inline_service_icons
        return inline_service_icons
    elif name == "inline_video_requests":
        from services.inline import video_requests as inline_video_requests
        return inline_video_requests
    elif name == "link_detection":
        from services.links import detection as link_detection
        return link_detection
    elif name == "pending_requests":
        from services.runtime import pending_requests
        return pending_requests
    elif name == "runtime_state_store":
        from services.runtime import state_store as runtime_state_store
        return runtime_state_store
    elif name == "runtime_stats":
        from services.runtime import stats as runtime_stats
        return runtime_stats
    elif name == "db":
        from services.storage import db
        return db
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "db",
    "download_queue",
    "download_worker_cli",
    "inline_album_links",
    "inline_service_icons",
    "inline_video_requests",
    "link_detection",
    "pending_requests",
    "runtime_state_store",
    "runtime_stats",
]

