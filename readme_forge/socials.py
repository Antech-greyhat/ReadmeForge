"""Social link badges for the Connect section."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Social:
    label: str
    logo: str
    color: str
    # None means the network has no per-user URL, so the badge is rendered unlinked.
    href: str | None
    strip_at: bool = False
    schemes: tuple[str, ...] = ("http", "https")

    def link(self, handle: str) -> str | None:
        return None if self.href is None else self.href.format(handle)


SOCIALS: dict[str, Social] = {
    "twitter": Social("X", "x", "000000", "https://x.com/{}", strip_at=True),
    "linkedin": Social(
        "LinkedIn", "linkedin", "0A66C2", "https://www.linkedin.com/in/{}", strip_at=True
    ),
    "email": Social("Email", "gmail", "EA4335", "mailto:{}", schemes=("mailto",)),
    "devto": Social("dev.to", "devdotto", "0A0A0A", "https://dev.to/{}", strip_at=True),
    "discord": Social("Discord", "discord", "5865F2", None),
    "stackoverflow": Social(
        "Stack Overflow", "stackoverflow", "F58025", "https://stackoverflow.com/users/{}"
    ),
    "youtube": Social("YouTube", "youtube", "FF0000", "https://youtube.com/@{}", strip_at=True),
    "website": Social("Website", "googlechrome", "7C6AF7", "{}"),
    "instagram": Social(
        "Instagram", "instagram", "E4405F", "https://www.instagram.com/{}", strip_at=True
    ),
    "facebook": Social(
        "Facebook", "facebook", "1877F2", "https://www.facebook.com/{}", strip_at=True
    ),
    "gitlab": Social("GitLab", "gitlab", "FC6D26", "https://gitlab.com/{}", strip_at=True),
    "bitbucket": Social(
        "Bitbucket", "bitbucket", "0052CC", "https://bitbucket.org/{}", strip_at=True
    ),
}

SOCIAL_KEYS: tuple[str, ...] = tuple(SOCIALS)
