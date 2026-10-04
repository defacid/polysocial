"""Validate posts before they enter the delivery queue."""

import base64
import binascii


IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_TYPES = {"video/mp4"}
PLATFORM_LIMITS = {
    "bluesky": {"count": 4, "bytes": 2 * 1024 * 1024},
    "facebook": {"count": 10, "bytes": 10 * 1024 * 1024},
    "instagram": {"count": 10, "bytes": 8 * 1024 * 1024},
    "threads": {"count": 10, "bytes": 8 * 1024 * 1024},
}


def validate_post(post):
    errors = []
    text = post.get("text")
    media = post.get("media")
    destinations = post.get("destinations")
    if not isinstance(text, str) or not isinstance(media, list) or not isinstance(destinations, dict):
        return ["Post fields are invalid"]
    if not text.strip() and not media:
        errors.append("Write a post or attach an image")
    if len(text) > 100_000:
        errors.append("Post text is too large")

    decoded = []
    for index, item in enumerate(media):
        if not isinstance(item, dict) or item.get("type") not in IMAGE_TYPES | VIDEO_TYPES:
            errors.append(f"Attachment {index + 1} must be a JPEG, PNG, WebP, or MP4 file")
            continue
        try:
            content = base64.b64decode(item.get("data", ""), validate=True)
        except (ValueError, binascii.Error):
            errors.append(f"Attachment {index + 1} is not valid base64 data")
            continue
        if not content:
            errors.append(f"Attachment {index + 1} is empty")
        if len(item.get("alt", "")) > 2000:
            errors.append(f"Attachment {index + 1} alt text is too long")
        decoded.append((index, len(content)))

    selected = {name for name, value in destinations.items() if value != "none"}
    videos = [item for item in media if item.get("type") in VIDEO_TYPES]
    if len(videos) > 1 or (videos and len(media) > 1):
        errors.append("Attach either images or one MP4 video")
    unknown = selected - PLATFORM_LIMITS.keys()
    if unknown:
        errors.append(f"Unsupported destination: {sorted(unknown)[0]}")
    for platform in selected & PLATFORM_LIMITS.keys():
        limit = PLATFORM_LIMITS[platform]
        if len(media) > limit["count"]:
            errors.append(f"{platform.title()} allows at most {limit['count']} images")
        for index, size in decoded:
            is_video = media[index].get("type") in VIDEO_TYPES
            byte_limit = 50 * 1024 * 1024 if is_video else limit["bytes"]
            if size > byte_limit:
                errors.append(f"Attachment {index + 1} exceeds {platform.title()}'s {byte_limit // 1024 // 1024} MB limit")
    if "instagram" in selected and not media:
        errors.append("Instagram requires an image or video")
    return errors
