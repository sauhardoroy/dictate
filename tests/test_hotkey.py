"""Unit tests for hotkey parsing and virtual-key mappings."""
import pytest
from hotkey.manager import get_vk, parse_combo, build_combo_name, is_modifier


def test_parse_combo_bracket_keys():
    # Left bracket
    mods, vk = parse_combo("ctrl+alt+[")
    assert mods == [0x11, 0x12]
    assert vk == 0xDB  # VK_OEM_4

    # Right bracket
    mods, vk = parse_combo("ctrl+alt+]")
    assert mods == [0x11, 0x12]
    assert vk == 0xDD  # VK_OEM_6

    # Named brackets
    mods, vk = parse_combo("ctrl+alt+left bracket")
    assert mods == [0x11, 0x12]
    assert vk == 0xDB

    mods, vk = parse_combo("ctrl+shift+}")
    assert mods == [0x11, 0x10]
    assert vk == 0xDD


def test_parse_combo_punctuation_keys():
    # Semicolon
    mods, vk = parse_combo("ctrl+alt+;")
    assert vk == 0xBA

    # Quote
    mods, vk = parse_combo("ctrl+alt+'")
    assert vk == 0xDE

    # Slash
    mods, vk = parse_combo("ctrl+/")
    assert vk == 0xBF

    # Minus
    mods, vk = parse_combo("alt+-")
    assert vk == 0xBD

    # Equal
    mods, vk = parse_combo("ctrl+=")
    assert vk == 0xBB


def test_parse_combo_alphanumeric_and_function_keys():
    mods, vk = parse_combo("ctrl+shift+p")
    assert mods == [0x11, 0x10]
    assert vk == ord("P")

    mods, vk = parse_combo("alt+f9")
    assert mods == [0x12]
    assert vk == 0x78

    mods, vk = parse_combo("f12")
    assert mods == []
    assert vk == 0x7B


def test_build_combo_name():
    assert build_combo_name(["alt", "ctrl"], "[") == "ctrl+alt+["
    assert build_combo_name(["shift", "ctrl"], "p") == "ctrl+shift+p"
