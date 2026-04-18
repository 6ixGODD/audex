from __future__ import annotations

from nicegui import ui

from audex.config.core.ui import UIInputMode


def _get_default_mode() -> UIInputMode:
    try:
        from audex.config import getconfig
        return getconfig().core.ui.input_mode
    except Exception:
        return UIInputMode.AUTO


def _ensure_assets() -> None:
    """Inject CSS/JS once per client connection."""
    try:
        from nicegui import context
        client = context.client
        if getattr(client, '_audex_oi_loaded', False):
            return
        client._audex_oi_loaded = True
    except Exception:
        pass
    ui.add_head_html('<link rel="stylesheet" href="/static/css/overlay_input.css">')
    ui.add_head_html('<script src="/static/js/overlay_input.js"></script>')


def _bind_dblclick(el: ui.element, mode_str: str) -> None:
    """
    Attach a NiceGUI dblclick handler as a reliable fallback.

    The document-level JS delegation handles most cases; this path fires via
    NiceGUI's own event routing so it works even if composedPath is shadowed.
    `el.id` is the integer NiceGUI element id; the DOM id is "c{el.id}".
    """
    dom_id = f"c{el.id}"

    async def _on_dblclick() -> None:
        await ui.run_javascript(
            f'window.AudexOverlayInput && window.AudexOverlayInput.triggerById("{dom_id}", "{mode_str}")'
        )

    el.on("dblclick", _on_dblclick)


def overlay_input(
    label: str = "",
    *,
    placeholder: str = "",
    mode: UIInputMode | None = None,
    password: bool = False,
    password_toggle_button: bool = False,
) -> ui.input:
    """Drop-in replacement for ui.input() with fullscreen overlay on double-click.

    On Linux tablets the on-screen keyboard covers the focused field.  This
    component shows a blurred fullscreen backdrop with a pill-shaped input
    anchored to the top of the screen, leaving room for the virtual keyboard.

    Args:
        label: Quasar input label (usually left empty – use placeholder instead).
        placeholder: Placeholder text shown inside the input.
        mode: Overlay behaviour.  Reads from ``config.core.ui.input_mode`` when
              ``None`` (the default).
        password: Mask input characters.
        password_toggle_button: Show show/hide toggle button.

    Returns:
        The underlying ``ui.input`` element – all NiceGUI fluent calls
        (``.classes()``, ``.props()``, ``.on()``, …) work as normal.
    """
    _ensure_assets()
    resolved = mode if mode is not None else _get_default_mode()

    inp = ui.input(
        label,
        placeholder=placeholder,
        password=password,
        password_toggle_button=password_toggle_button,
    )
    inp.classes(f"audex-oi-{resolved}")
    _bind_dblclick(inp, resolved)
    return inp


def overlay_textarea(
    label: str = "",
    *,
    placeholder: str = "",
    mode: UIInputMode | None = None,
) -> ui.textarea:
    """Drop-in replacement for ui.textarea() with fullscreen overlay on double-click.

    Same behaviour as :func:`overlay_input` but for multi-line text areas.
    Pressing **Ctrl+Enter** confirms; **Esc** cancels without saving.

    Args:
        label: Quasar textarea label.
        placeholder: Placeholder text.
        mode: Overlay behaviour.  Reads from ``config.core.ui.input_mode`` when
              ``None``.

    Returns:
        The underlying ``ui.textarea`` element.
    """
    _ensure_assets()
    resolved = mode if mode is not None else _get_default_mode()

    ta = ui.textarea(label, placeholder=placeholder)
    ta.classes(f"audex-oi-{resolved}")
    _bind_dblclick(ta, resolved)
    return ta
