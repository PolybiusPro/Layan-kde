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
- Konsole color schemes and translucent profiles (matching Dolphin)
- layan-dark-cursors, layan-light-cursors and layan-darker-cursors (rounded, derived from Breeze Dark)

## Installation

```sh
# Install for your user (recommended)
./install.sh --apply

# Install system-wide for all users
sudo ./install.sh --system --apply
```

`--apply` activates the Layan global theme (look-and-feel) after files are installed.
Use `--apply-light` for the light variant.

In Konsole, choose the **Layan** or **LayanLight** profile under Settings → Profiles.
Both use blurred transparency and the same purple accent (`#5657f5`) as Dolphin.

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
./uninstall.sh
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
