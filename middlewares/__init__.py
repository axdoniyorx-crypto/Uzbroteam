from .antiflood import AntifloodMiddleware
from .ban_middleware import UserBannedMiddleware
from .bot_enabled_guard import BotEnabledGuardMiddleware
from .chat_tracker import ChatTrackerMiddleware
from .private_chat_guard import PrivateChatGuardMiddleware
from .subscription_check import SubscriptionCheckMiddleware

# Mandatory-channel-subscription enforcement is controlled at runtime by an
# admin-panel on/off toggle (see services/subscription.py and
# handlers/admin_extended.py: "admin_toggle_mandatory_subscription"). The
# middleware below always runs, but checks that toggle first and does
# nothing when the feature is disabled, so leaving it registered here is
# always safe. BotEnabledGuardMiddleware runs first so a fully-disabled
# bot short-circuits before any other checks.
__all__ = [
    BotEnabledGuardMiddleware,
    AntifloodMiddleware,
    UserBannedMiddleware,
    PrivateChatGuardMiddleware,
    ChatTrackerMiddleware,
    SubscriptionCheckMiddleware,
]
