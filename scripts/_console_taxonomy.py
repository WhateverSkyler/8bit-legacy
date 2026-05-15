"""Canonical console taxonomy — strict mappings, no fuzzy/substring matching.

PriceCharting labels consoles differently than our Shopify tags. This module
is the single source of truth: every PC label and every Shopify tag maps to
exactly one canonical console ID. Cross-console matching requires ID equality.

This replaces the previous fuzzy `"wii" in "wii u"` check that caused the
2026-04/05 Wii ↔ Wii U price corruption.
"""
from __future__ import annotations


# Each entry: canonical_id -> { pc_labels: set, shopify_tags: set, family: str }
# Labels and tags are all lowercase, stripped.
CONSOLES: dict[str, dict] = {
    "nes": {
        "pc_labels": {"nes", "nintendo (nes)", "nintendo nes"},
        "shopify_tags": {"nes"},
        "family": "nintendo_classic",
    },
    "snes": {
        "pc_labels": {"super nintendo", "snes"},
        "shopify_tags": {"snes", "super nintendo"},
        "family": "nintendo_classic",
    },
    "n64": {
        "pc_labels": {"nintendo 64"},
        "shopify_tags": {"n64", "nintendo 64"},
        "family": "nintendo_classic",
    },
    "gamecube": {
        "pc_labels": {"gamecube", "nintendo gamecube"},
        "shopify_tags": {"gamecube", "nintendo gamecube"},
        "family": "nintendo_home",
    },
    "wii": {
        "pc_labels": {"wii"},
        "shopify_tags": {"wii"},
        "family": "nintendo_home",
    },
    "wii_u": {
        "pc_labels": {"wii u"},
        "shopify_tags": {"wii u"},
        "family": "nintendo_home",
    },
    "gameboy": {
        "pc_labels": {"gameboy", "game boy"},
        "shopify_tags": {"gameboy", "game boy"},
        "family": "nintendo_handheld",
    },
    "gameboy_color": {
        "pc_labels": {"gameboy color", "game boy color"},
        "shopify_tags": {"gameboy color", "game boy color"},
        "family": "nintendo_handheld",
    },
    "gba": {
        "pc_labels": {"gameboy advance", "game boy advance"},
        "shopify_tags": {"gba", "gameboy advance", "game boy advance"},
        "family": "nintendo_handheld",
    },
    "ds": {
        "pc_labels": {"nintendo ds"},
        "shopify_tags": {"nintendo ds", "ds"},
        "family": "nintendo_handheld",
    },
    "ds_3ds": {
        "pc_labels": {"nintendo 3ds"},
        "shopify_tags": {"nintendo 3ds", "3ds"},
        "family": "nintendo_handheld",
    },
    "switch": {
        "pc_labels": {"nintendo switch"},
        "shopify_tags": {"nintendo switch", "switch"},
        "family": "nintendo_modern",
    },
    "ps1": {
        "pc_labels": {"playstation"},
        "shopify_tags": {"playstation", "ps1", "psx"},
        "family": "sony_home",
    },
    "ps2": {
        "pc_labels": {"playstation 2"},
        "shopify_tags": {"playstation 2", "ps2"},
        "family": "sony_home",
    },
    "ps3": {
        "pc_labels": {"playstation 3"},
        "shopify_tags": {"playstation 3", "ps3"},
        "family": "sony_home",
    },
    "ps4": {
        "pc_labels": {"playstation 4"},
        "shopify_tags": {"playstation 4", "ps4"},
        "family": "sony_home",
    },
    "psp": {
        "pc_labels": {"psp"},
        "shopify_tags": {"psp"},
        "family": "sony_handheld",
    },
    "ps_vita": {
        "pc_labels": {"playstation vita", "ps vita"},
        "shopify_tags": {"ps vita", "playstation vita", "vita"},
        "family": "sony_handheld",
    },
    "xbox": {
        "pc_labels": {"xbox"},
        "shopify_tags": {"xbox"},
        "family": "microsoft",
    },
    "xbox_360": {
        "pc_labels": {"xbox 360"},
        "shopify_tags": {"xbox 360"},
        "family": "microsoft",
    },
    "sega_master_system": {
        "pc_labels": {"sega master system", "master system"},
        "shopify_tags": {"sega master system", "master system"},
        "family": "sega_classic",
    },
    "sega_genesis": {
        "pc_labels": {"sega genesis", "genesis"},
        "shopify_tags": {"sega genesis", "genesis"},
        "family": "sega_classic",
    },
    "sega_32x": {
        "pc_labels": {"sega 32x", "32x", "genesis 32x"},
        "shopify_tags": {"sega 32x", "32x"},
        "family": "sega_classic",
    },
    "sega_cd": {
        "pc_labels": {"sega cd", "mega cd"},
        "shopify_tags": {"sega cd"},
        "family": "sega_classic",
    },
    "sega_saturn": {
        "pc_labels": {"sega saturn", "saturn"},
        "shopify_tags": {"sega saturn", "saturn"},
        "family": "sega_home",
    },
    "sega_dreamcast": {
        "pc_labels": {"sega dreamcast", "dreamcast"},
        "shopify_tags": {"sega dreamcast", "dreamcast"},
        "family": "sega_home",
    },
    "sega_game_gear": {
        "pc_labels": {"sega game gear", "game gear"},
        "shopify_tags": {"sega game gear", "game gear"},
        "family": "sega_handheld",
    },
    "atari_2600": {
        "pc_labels": {"atari 2600"},
        "shopify_tags": {"atari 2600"},
        "family": "atari",
    },
    "atari_5200": {
        "pc_labels": {"atari 5200"},
        "shopify_tags": {"atari 5200"},
        "family": "atari",
    },
    "atari_7800": {
        "pc_labels": {"atari 7800"},
        "shopify_tags": {"atari 7800"},
        "family": "atari",
    },
    "atari_lynx": {
        "pc_labels": {"atari lynx", "lynx"},
        "shopify_tags": {"atari lynx", "lynx"},
        "family": "atari",
    },
    "turbografx_16": {
        "pc_labels": {"turbografx-16", "turbografx 16", "turbografx16"},
        "shopify_tags": {"turbografx", "turbografx-16", "turbografx 16"},
        "family": "nec",
    },
}

# Reverse lookups, built once at import.
_PC_LABEL_TO_ID: dict[str, str] = {}
_TAG_TO_ID: dict[str, str] = {}
for _id, _data in CONSOLES.items():
    for _lbl in _data["pc_labels"]:
        _PC_LABEL_TO_ID[_lbl] = _id
    for _tag in _data["shopify_tags"]:
        _TAG_TO_ID[_tag] = _id


def _norm(s: str) -> str:
    return s.lower().strip()


def pc_label_to_id(pc_label: str) -> str | None:
    """Map a PriceCharting console label to canonical ID. STRICT — no fuzzy."""
    if not pc_label:
        return None
    return _PC_LABEL_TO_ID.get(_norm(pc_label))


def tag_to_id(tag: str) -> str | None:
    """Map a Shopify console tag (or our internal console name) to canonical ID. STRICT."""
    if not tag:
        return None
    return _TAG_TO_ID.get(_norm(tag))


def same_console(pc_label: str, target_tag: str) -> bool:
    """True iff PC label and target tag resolve to the same canonical console.

    The previous fuzzy `"wii" in "wii u"` check returned True (incorrectly).
    This returns False — strict equality.
    """
    pc_id = pc_label_to_id(pc_label)
    tag_id = tag_to_id(target_tag)
    if pc_id is None or tag_id is None:
        return False
    return pc_id == tag_id


def family(console_id: str) -> str | None:
    data = CONSOLES.get(console_id)
    return data["family"] if data else None


def same_family(pc_label: str, target_tag: str) -> bool:
    """True iff they share a family. Used for veto-style cross-family warnings."""
    pc_id = pc_label_to_id(pc_label)
    tag_id = tag_to_id(target_tag)
    if pc_id is None or tag_id is None:
        return False
    return family(pc_id) == family(tag_id)
