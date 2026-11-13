#!/usr/bin/env python3
"""Generate the Layan and Layan-light GTK themes from the Plasma color schemes.

The palette is read from color-schemes/Layan.colors and LayanLight.colors, so GTK
applications use the same colors as the Qt ones. Each theme contains:

  gtk-3.0/gtk.css         imports Breeze-GTK (breeze-gtk package), then overrides its named
                          colors with the Layan palette and rounds windows, menus and tooltips.
                          Also restyles what Chromium-based browsers draw in their own title bar:
                          the window buttons like the Layan Aurorae decoration, and tab and
                          toolbar colors that make the active tab stand out. Their windows keep
                          square corners
  gtk-3.0/assets/         glyphs for those window buttons
  gtk-4.0/gtk.css         the same for GTK 4, without the window buttons
  gtk-4.0/libadwaita.css  the palette as libadwaita named colors. libadwaita apps ignore the
                          theme name, so install.sh imports this file from
                          ~/.config/gtk-4.0/gtk.css

Breeze-GTK exposes every color as a named color ending in _breeze, which is the hook
kde-gtk-config uses to follow the active Plasma color scheme. This does the same for Layan,
so the theme also works outside Plasma and when kde-gtk-config is not running.

The generated themes are checked in, so users never need to run this.

Usage: generate.py
"""
import configparser
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

VARIANTS = [
    # theme name, Breeze theme to import, color scheme, dark?
    ("Layan", "Breeze-Dark", "Layan.colors", True),
    ("Layan-light", "Breeze", "LayanLight.colors", False),
]

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Brighter semantic colors for libadwaita, which uses them as text on the window background
ADW_SUCCESS = {True: (0x3D, 0xD6, 0x8C), False: (0x00, 0x6E, 0x28)}
ADW_WARNING = {True: (0xF5, 0xC2, 0x11), False: (0xB0, 0x80, 0x00)}
ADW_ERROR = {True: (0xFF, 0x5C, 0x5C), False: (0xBF, 0x03, 0x03)}


def load_scheme(path):
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    cp.read(path)

    def color(section, key):
        # Some foregrounds carry an alpha channel as a fourth value, which is dropped
        r, g, b = (int(v) for v in cp[f"Colors:{section}"][key].split(",")[:3])
        return (r, g, b)

    return color


def mix(a, b, t):
    """a * (1 - t) + b * t"""
    return tuple(x * (1 - t) + y * t for x, y in zip(a, b))


def css(c, alpha=None):
    if isinstance(c, str):
        return c
    r, g, b = (round(v) for v in c)
    if alpha is None:
        return "#%02x%02x%02x" % (r, g, b)
    return "rgba(%d, %d, %d, %s)" % (r, g, b, alpha)


class Palette:
    def __init__(self, scheme, dark):
        c = load_scheme(os.path.join(ROOT, "color-schemes", scheme))
        self.dark = dark
        self.bg = c("Window", "BackgroundNormal")
        self.fg = c("Window", "ForegroundNormal")
        self.base = c("View", "BackgroundNormal")
        self.text = c("View", "ForegroundNormal")
        self.button = c("Button", "BackgroundNormal")
        self.button_fg = c("Button", "ForegroundNormal")
        self.header = c("Header", "BackgroundNormal")
        self.header_fg = c("Header", "ForegroundNormal")
        self.tooltip = c("Tooltip", "BackgroundNormal")
        self.tooltip_fg = c("Tooltip", "ForegroundNormal")
        self.accent = c("Selection", "BackgroundNormal")
        self.accent_fg = c("Selection", "ForegroundNormal")
        self.link = c("Window", "ForegroundLink")
        self.visited = c("Window", "ForegroundVisited")
        self.positive = c("Window", "ForegroundPositive")
        self.neutral = c("Window", "ForegroundNeutral")
        self.negative = c("Window", "ForegroundNegative")

        self.border = mix(self.bg, self.fg, 0.2)
        self.insensitive_border = mix(self.bg, self.fg, 0.07)
        self.insensitive_fg = mix(self.bg, self.fg, 0.35)
        self.unfocused_bg = mix(self.bg, self.fg, 0.01)
        self.unfocused_fg = mix(self.bg, self.fg, 0.98)
        self.unfocused_accent = mix(BLACK, self.accent, 0.58)
        self.backdrop_accent = mix(self.accent, (128, 128, 128), 0.3)
        self.insensitive_accent = mix(self.accent, self.bg, 0.5)
        self.card = mix(self.bg, self.fg, 0.06)
        self.popover = mix(self.bg, self.fg, 0.08) if dark else self.button
        self.sidebar = mix(self.bg, BLACK, 0.12 if dark else 0.03)


def breeze_palette(p):
    """Values for the *_breeze named colors that Breeze-GTK defines."""
    c = {}

    def semantic(name, color):
        c[f"{name}_breeze"] = css(color)
        c[f"{name}_backdrop_breeze"] = css(mix(color, p.bg, 0.1))
        c[f"{name}_insensitive_breeze"] = css(mix(color, p.bg, 0.6))
        c[f"{name}_insensitive_backdrop_breeze"] = css(mix(color, p.bg, 0.6))

    c.update(
        {
            # Window and view
            "theme_bg_color_breeze": css(p.bg),
            "theme_fg_color_breeze": css(p.fg),
            "theme_base_color_breeze": css(p.base),
            "theme_text_color_breeze": css(p.text),
            "content_view_bg_breeze": css(p.base),
            "theme_selected_bg_color_breeze": css(p.accent),
            "theme_selected_fg_color_breeze": css(p.accent_fg),
            "theme_hovering_selected_bg_color_breeze": css(p.accent),
            "theme_view_hover_decoration_color_breeze": css(p.accent),
            "theme_view_active_decoration_color_breeze": css(p.accent),
            "link_color_breeze": css(p.link),
            "link_visited_color_breeze": css(p.visited),
            "borders_breeze": css(p.border),
            "unfocused_borders_breeze": css(p.border),
            "insensitive_borders_breeze": css(p.insensitive_border),
            "unfocused_insensitive_borders_breeze": css(p.insensitive_border),
            # Unfocused and insensitive
            "theme_unfocused_bg_color_breeze": css(p.unfocused_bg),
            "theme_unfocused_base_color_breeze": css(p.unfocused_bg),
            "theme_unfocused_fg_color_breeze": css(p.unfocused_fg),
            "theme_unfocused_text_color_breeze": css(p.unfocused_fg),
            "theme_unfocused_selected_bg_color_breeze": css(p.unfocused_accent),
            "theme_unfocused_selected_bg_color_alt_breeze": css(p.unfocused_accent),
            "theme_unfocused_selected_fg_color_breeze": css(mix(p.accent_fg, p.bg, 0.1)),
            "theme_unfocused_view_bg_color_breeze": css(p.base),
            "theme_unfocused_view_text_color_breeze": css(p.insensitive_fg),
            "insensitive_bg_color_breeze": css(p.bg),
            "insensitive_fg_color_breeze": css(p.insensitive_fg),
            "insensitive_base_color_breeze": css(p.base),
            "insensitive_base_fg_color_breeze": css(p.insensitive_fg),
            "insensitive_selected_bg_color_breeze": css(p.bg),
            "insensitive_selected_fg_color_breeze": css(p.insensitive_fg),
            "insensitive_unfocused_bg_color_breeze": css(p.bg),
            "insensitive_unfocused_fg_color_breeze": css(p.insensitive_fg),
            "insensitive_unfocused_selected_bg_color_breeze": css(p.bg),
            "insensitive_unfocused_selected_fg_color_breeze": css(p.insensitive_fg),
            # Buttons
            "theme_button_background_normal_breeze": css(p.button),
            "theme_button_background_insensitive_breeze": css(p.button),
            "theme_button_background_backdrop_breeze": css(p.button),
            "theme_button_background_backdrop_insensitive_breeze": css(p.button),
            "theme_button_foreground_normal_breeze": css(p.button_fg),
            "theme_button_foreground_backdrop_breeze": css(mix(p.bg, p.button_fg, 0.98)),
            "theme_button_foreground_insensitive_breeze": css(mix(p.button, p.fg, 0.35)),
            "theme_button_foreground_backdrop_insensitive_breeze": css(
                mix(p.button, p.fg, 0.35)
            ),
            "theme_button_foreground_active_breeze": css(p.accent_fg),
            "theme_button_foreground_active_backdrop_breeze": css(mix(p.accent_fg, p.bg, 0.1)),
            "theme_button_foreground_active_insensitive_breeze": css(p.insensitive_fg),
            "theme_button_foreground_active_backdrop_insensitive_breeze": css(p.insensitive_fg),
            # Titlebars
            "theme_titlebar_background_breeze": css(p.header),
            "theme_titlebar_background_light_breeze": css(p.header),
            "theme_titlebar_background_backdrop_breeze": css(p.unfocused_bg),
            "theme_titlebar_foreground_breeze": css(p.header_fg),
            "theme_titlebar_foreground_backdrop_breeze": css(p.unfocused_fg),
            "theme_titlebar_foreground_insensitive_breeze": css(p.unfocused_fg),
            "theme_titlebar_foreground_insensitive_backdrop_breeze": css(p.unfocused_fg),
            # Tooltips
            "tooltip_background_breeze": css(p.tooltip),
            "tooltip_text_breeze": css(p.tooltip_fg),
            "tooltip_border_breeze": css(mix(p.tooltip, p.tooltip_fg, 0.2)),
        }
    )
    for state in ("hover", "focus"):
        c[f"theme_button_decoration_{state}_breeze"] = css(p.accent)
        c[f"theme_button_decoration_{state}_insensitive_breeze"] = css(p.insensitive_accent)
        c[f"theme_button_decoration_{state}_backdrop_breeze"] = css(p.backdrop_accent)
        c[f"theme_button_decoration_{state}_backdrop_insensitive_breeze"] = css(
            p.insensitive_accent
        )
    semantic("success_color", p.positive)
    semantic("warning_color", p.neutral)
    semantic("error_color", p.negative)
    return c


def adwaita_palette(p):
    """libadwaita named colors."""
    d = p.dark
    c = {
        "accent_color": mix(p.accent, WHITE, 0.25) if d else p.accent,
        "accent_bg_color": p.accent,
        "accent_fg_color": p.accent_fg,
        "destructive_color": ADW_ERROR[d],
        "destructive_bg_color": mix(ADW_ERROR[d], BLACK, 0.25) if d else ADW_ERROR[d],
        "destructive_fg_color": WHITE,
        "success_color": ADW_SUCCESS[d],
        "success_bg_color": mix(ADW_SUCCESS[d], BLACK, 0.45) if d else ADW_SUCCESS[d],
        "success_fg_color": WHITE,
        "warning_color": ADW_WARNING[d],
        "warning_bg_color": mix(ADW_WARNING[d], BLACK, 0.45) if d else ADW_WARNING[d],
        "warning_fg_color": WHITE,
        "error_color": ADW_ERROR[d],
        "error_bg_color": mix(ADW_ERROR[d], BLACK, 0.25) if d else ADW_ERROR[d],
        "error_fg_color": WHITE,
        "window_bg_color": p.bg,
        "window_fg_color": p.fg,
        "view_bg_color": p.base,
        "view_fg_color": p.text,
        "headerbar_bg_color": p.header,
        "headerbar_fg_color": p.header_fg,
        "headerbar_border_color": "rgb(%s / 12%%)" % ("255 255 255" if d else "0 0 0"),
        "headerbar_backdrop_color": p.bg,
        "headerbar_shade_color": "rgb(0 0 0 / 12%)",
        "headerbar_darker_shade_color": "rgb(0 0 0 / 20%)",
        "sidebar_bg_color": p.sidebar,
        "sidebar_fg_color": p.fg,
        "sidebar_backdrop_color": p.bg,
        "sidebar_shade_color": "rgb(0 0 0 / 12%)",
        "sidebar_border_color": "rgb(0 0 0 / 12%)",
        "secondary_sidebar_bg_color": p.sidebar,
        "secondary_sidebar_fg_color": p.fg,
        "secondary_sidebar_backdrop_color": p.bg,
        "secondary_sidebar_shade_color": "rgb(0 0 0 / 12%)",
        "secondary_sidebar_border_color": "rgb(0 0 0 / 12%)",
        "card_bg_color": p.card,
        "card_fg_color": p.fg,
        "card_shade_color": "rgb(0 0 0 / 8%)",
        "dialog_bg_color": p.bg,
        "dialog_fg_color": p.fg,
        "popover_bg_color": p.popover,
        "popover_fg_color": p.fg,
        "popover_shade_color": "rgb(0 0 0 / 12%)",
        "shade_color": "rgb(0 0 0 / %d%%)" % (25 if d else 7),
        "scrollbar_outline_color": "rgb(0 0 0 / %d%%)" % (50 if d else 0),
        "thumbnail_bg_color": p.card,
        "thumbnail_fg_color": p.fg,
    }
    return c


def defines(colors):
    return "\n".join(f"@define-color {n} {css(v)};" for n, v in colors.items())


# Breeze rounds controls itself (and keeps the inner corners of linked groups square), so only
# the surfaces it leaves nearly square are rounded here.
SHAPE_GTK3 = """\
window.csd,
window.csd decoration {
  border-radius: 12px 12px 0 0;
}

window.csd.popup,
window.csd.popup decoration,
window.csd.tooltip,
window.csd.tooltip decoration,
window.csd.menu,
window.csd.menu decoration {
  border-radius: 8px;
}

window.maximized,
window.tiled,
window.fullscreen,
window.maximized decoration,
window.tiled decoration,
window.fullscreen decoration {
  border-radius: 0;
}

menu,
.menu,
.popup {
  border-radius: 8px;
}

tooltip.background,
tooltip {
  border-radius: 8px;
}
"""

SHAPE_GTK4 = """\
window.csd {
  border-radius: 12px;
}

window.maximized,
window.tiled,
window.fullscreen {
  border-radius: 0;
}

popover.background > contents,
popover > arrow {
  border-radius: 8px;
}

tooltip.background {
  border-radius: 8px;
}
"""

# Window buttons: the round dots of the Layan Aurorae decoration (aurorae/themes/Layan). A gray
# dot at rest, a glyph on hover, red for close and the accent when pressed, darker when the
# window is unfocused. Breeze-GTK paints Chromium's buttons with PNGs through selectors that
# contain "window.background.chromium", so these use the same selectors to take over.
BUTTON_GLYPHS = {
    "close": '<path d="M5 5L11 11M11 5L5 11"/>',
    "minimize": '<path d="M4.5 8H11.5"/>',
    "maximize": '<rect x="4.5" y="4.5" width="7" height="7" rx="0.5"/>',
    "maximized": '<rect x="4.5" y="6.5" width="5" height="5" rx="0.5"/>'
    '<path d="M6.5 6.5V4.5H11.5V9.5H9.5"/>',
}

BUTTON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" '
    'fill="none" stroke="#ffffff" stroke-width="1.3" stroke-linecap="round" '
    'stroke-linejoin="round">{}</svg>\n'
)


def titlebuttons_gtk3(p):
    # The dark and light Aurorae themes use the same colors, so both variants share them
    prefix = "window.background.chromium"
    dot = "rgba(178, 178, 178, 0.5)"
    unfocused = "rgba(136, 136, 136, 0.5)"
    pressed = css(p.accent)
    out = []

    def rule(selectors, body):
        out.append(",\n".join(selectors) + " {\n" + body + "}\n")

    def sel(name, state="", maximized=False):
        win = prefix + (".maximized" if maximized else "")
        base = f"button.titlebutton.{name}{state}"
        return [f"{win} headerbar {base}", f"{win} .titlebar {base}"]

    def image(glyph):
        return "none" if glyph is None else f'url("assets/layan-{glyph}.svg")'

    shape = (
        "  color: transparent;\n"
        "  border-image: none;\n"
        "  border-color: transparent;\n"
        "  border-radius: 50%;\n"
        "  box-shadow: none;\n"
        "  -gtk-icon-source: none;\n"
        "  min-width: 16px;\n"
        "  min-height: 16px;\n"
        "  padding: 0;\n"
        "  margin: 0 4px;\n"
        "  background-repeat: no-repeat;\n"
        "  background-position: center;\n"
        "  background-size: 16px 16px;\n"
    )

    # name, glyph at rest, hover color, pressed color
    for name, glyph, hover, press, maximized in (
        ("close", "close", "#ff5555", pressed, False),
        ("minimize", "minimize", dot, "rgba(179, 179, 179, 0.5)", False),
        ("maximize", "maximize", dot, "rgba(179, 179, 179, 0.5)", False),
        ("maximize", "maximized", dot, "rgba(179, 179, 179, 0.5)", True),
    ):
        rule(
            sel(name, maximized=maximized),
            f"{shape}  background-color: {dot};\n  background-image: none;\n",
        )
        rule(
            sel(name, ":hover", maximized),
            f"  background-color: {hover};\n  background-image: {image(glyph)};\n",
        )
        rule(
            sel(name, ":active", maximized),
            f"  background-color: {press};\n  background-image: {image(glyph)};\n",
        )
        rule(
            sel(name, ":backdrop", maximized),
            f"  background-color: {unfocused};\n  background-image: none;\n",
        )
    return "\n".join(out)


def window_shadow_gtk3(p):
    """Lighter shadow for regular windows than the Breeze default.

    Breeze draws 0 0 16px at 50% plus 0 2px 8px at 30%, which is very heavy. Popups, tooltips and
    message dialogs keep their own Breeze shadows, which are more specific than this selector.
    """
    blur, ring = ("0.22", "0.2") if p.dark else ("0.15", "0.12")
    return (
        "window.csd decoration {\n"
        f"  box-shadow: 0 2px 8px rgba(0, 0, 0, {blur}), 0 0 0 1px rgba(0, 0, 0, {ring});\n"
        "}\n"
    )


# Chromium-based browsers get square corners. The window outline comes from the decoration node and
# the title bar from the headerbar nodes, so all of them are flattened, and the shadow then follows
# the square outline. These selectors are more specific than the generic window.csd rules above.
CHROMIUM_SHAPE_GTK3 = """\
window.background.chromium,
window.background.chromium decoration,
window.csd.chromium,
window.csd.chromium decoration,
window.background.chromium headerbar,
window.background.chromium headerbar.titlebar,
window.background.chromium .titlebar {
  border-radius: 0;
}
"""


def chromium_tabs_gtk3(p):
    """Make the active tab stand out in Chromium-based browsers.

    Chromium takes the toolbar, infobars and the active tab from the window background, and the
    tab strip behind them from the titlebar. Layan uses the same color for both, which leaves
    the active tab invisible. In the dark theme the toolbar and tab get darker than the frame,
    so the frame keeps the scheme's color. In the light theme the frame gets darker instead, so
    the tab stays the lighter surface. Scoped to Chromium so other GTK windows are unchanged.
    """
    prefix = "window.background.chromium"
    if p.dark:
        return f"{prefix} {{\n  background-color: {css(mix(p.bg, BLACK, 0.3))};\n}}\n"

    selectors = [f"{prefix} headerbar.titlebar", f"{prefix} .titlebar", f"{prefix} headerbar"]
    out = []
    for state, amount in (("", 0.12), (":backdrop", 0.1)):
        color = css(mix(p.bg, BLACK, amount))
        out.append(
            ",\n".join(s + state for s in selectors)
            + f" {{\n  background-color: {color};\n  background-image: none;\n}}\n"
        )
    return "\n".join(out)


HEADER = "/* Generated by gtk/generate.py from color-schemes/{scheme}. Do not edit by hand. */\n"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def build(name, breeze, scheme, dark):
    p = Palette(scheme, dark)
    out = os.path.join(HERE, "themes", name)
    head = HEADER.format(scheme=scheme)
    palette = defines(breeze_palette(p))

    write(
        os.path.join(out, "index.theme"),
        f"""[Desktop Entry]
Type=X-GNOME-Metatheme
Name={name}
Comment=Layan {"dark" if dark else "light"} theme for GTK, matching the Layan Plasma theme
Encoding=UTF-8

[X-GNOME-Metatheme]
GtkTheme={name}
MetacityTheme={name}
IconTheme=Tela{"-dark" if dark else ""}
CursorTheme={"layan-darker-cursors" if dark else "layan-light-cursors"}
""",
    )

    shape3 = "\n".join(
        (
            SHAPE_GTK3,
            window_shadow_gtk3(p),
            CHROMIUM_SHAPE_GTK3,
            chromium_tabs_gtk3(p),
            titlebuttons_gtk3(p),
        )
    )
    for ver, shape in (("3.0", shape3), ("4.0", SHAPE_GTK4)):
        write(
            os.path.join(out, f"gtk-{ver}", "gtk.css"),
            f'{head}@import url("../../{breeze}/gtk-{ver}/gtk.css");\n\n{palette}\n\n{shape}',
        )

    for glyph, shapes in BUTTON_GLYPHS.items():
        write(
            os.path.join(out, "gtk-3.0", "assets", f"layan-{glyph}.svg"),
            BUTTON_SVG.format(shapes),
        )

    write(
        os.path.join(out, "gtk-4.0", "libadwaita.css"),
        head + defines(adwaita_palette(p)) + "\n",
    )


def main():
    for name, breeze, scheme, dark in VARIANTS:
        build(name, breeze, scheme, dark)
        print("generated", name)


if __name__ == "__main__":
    main()
