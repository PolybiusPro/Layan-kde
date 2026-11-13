<p align="center">
  <img src="logo.png" alt="Layan logo" width="128" />
</p>

# Layan KDE

Layan kde is a flat Design theme for KDE Plasma desktop.

In this repository you'll find:

- Aurorae Themes
- Kvantum Themes
- Plasma Color Schemes
- Plasma Desktop Themes
- Plasma Look-and-Feel Themes
- GTK 3 and GTK 4 themes (Layan and Layan-light), including libadwaita apps
- Konsole color schemes and translucent profiles (matching Dolphin)
- layan-dark-cursors, layan-light-cursors and layan-darker-cursors (rounded, derived from Breeze Dark)

## Installation

```sh
sudo ./install.sh --apply
```

The installer only runs as root and installs system-wide under `/usr/share`, so every user and
the login screen can use the theme. The exception is the Aurorae window decoration, which is
installed into the invoking user's `~/.local/share/aurorae/themes`.

`--apply` activates the Layan global theme (look-and-feel) and the matching GTK theme for the user
who ran `sudo` after files are installed. Use `--apply-light` for the light variant.

In Konsole, choose the **Layan** or **LayanLight** profile under Settings → Profiles.
Both use blurred transparency and the same purple accent (`#5657f5`) as Dolphin.

## GTK applications

`install.sh` installs the **Layan** and **Layan-light** GTK themes (`gtk/themes/`) to
`/usr/share/themes`, and `--apply` selects the right one through kde-gtk-config. They cover GTK 3
and GTK 4 apps. The palette comes from `Layan.colors` and `LayanLight.colors`, so GTK and Qt apps
share the same colors.

- The themes import Breeze-GTK and override its colors, so the `breeze-gtk` package must be
  installed (kde-gtk-config already depends on it). Windows, menus, popovers and tooltips are
  rounded on top of that.
- libadwaita apps ignore the theme name. `--apply` adds an import of the Layan palette to
  `~/.config/gtk-4.0/gtk.css` (`uninstall.sh` removes it again).
- To pick a theme by hand, use System Settings -> Application Style -> Configure GNOME/GTK
  Application Style.
- Chromium-based browsers (Brave, Chrome) draw their own title bar. With **Use GTK** selected in
  the browser's Appearance settings, the GTK 3 themes style its minimize, maximize and close
  buttons like the Layan Aurorae decoration (round dots, red close on hover). The browser window
  itself has 9px corners.
- GTK 2 is not themed.

`gtk/generate.py` rebuilds the themes from the color schemes (python3 only).

## Cursors

`install.sh` installs three cursor themes (`cursors/`). Pick one under System Settings -> Cursors.

- **layan-dark-cursors**: Breeze Dark recolored to the layan accent (`#5657f5`) with a white
  outline. The arrow has Breeze's 45 degree tip and wingspan, a vertical left edge, mirror
  symmetry about its own axis, and proportions taken from the golden ratio. The other cursors
  have rounded corners and a 1 px outline of even thickness.
- **layan-light-cursors**: the same shapes with the colors swapped (white body, accent
  outline). Badges (help, copy, progress, ...) sit on a white disc with an accent ring.
- **layan-darker-cursors**: the dark theme with the accent replaced by the dark window
  background (`#31313a`, the Window color in `Layan.colors`), keeping the white outline. The
  center dots of the resize cursors are the accent blue.

The busy spinners (wait and progress) are the same in all three themes: three round arcs in
purple, green and teal, drawn from one geometry. Their fill follows the theme: accent in the
dark theme, white in the light theme and `#31313a` in the darker theme, with each color
adjusted to stay legible on it. The no-entry discs and the Wayland cursor are filled with grey
(`#b4b4b4`) in the dark theme and `#31313a` in the darker theme. The X cursor uses the same two
tones the other way round: a `#31313a` fill with grey arms in the dark theme, a grey fill with
`#31313a` arms in the darker theme.

`cursors/generate.py` rebuilds all three from an installed `breeze-cursors` (needs `rsvg-convert`,
fontTools, Pillow, numpy and lxml). Based on Breeze by the KDE VDG (LGPL-2.1-or-later).

## Uninstallation

```sh
sudo ./uninstall.sh
```

## Recommendations

- For better looking please use this pack with [Kvantum engine](https://github.com/tsujan/Kvantum/tree/master/Kvantum).

  Run `kvantummanager` to choose and apply **Layan** theme.

- Install [Tela icon theme](https://github.com/vinceliuice/Tela-icon-theme) for a more consistent and beautiful experience.

## Preview

![Layan dark](plasma/look-and-feel/com.github.vinceliuice.Layan/contents/previews/fullscreenpreview.jpg)

## Donate

If you like this theme, please support the original author on the upstream project:

[vinceliuice/Layan-kde](https://github.com/vinceliuice/Layan-kde)

## License

GNU GPL v3
