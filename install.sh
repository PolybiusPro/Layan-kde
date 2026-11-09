#!/bin/bash
set -euo pipefail

ROOT_UID=0
SRC_DIR=$(cd "$(dirname "$0")" && pwd)

THEME_NAME=Layan
COLOR_VARIANTS=('' '-light')
APPLY_THEME=""

usage() {
  cat <<EOF
Usage: sudo $(basename "$0") [OPTIONS]

Install Layan KDE theme components (Plasma desktop theme, color scheme,
look-and-feel / global theme, Konsole, Aurorae, Kvantum, GTK, cursors, wallpapers)
for all users under /usr/share. Must be run as root, so the login screen
(which runs as its own user) can see the theme too.

Options:
  --apply     Activate the dark Layan global theme and GTK theme for the invoking user
  --apply-light
              Activate the Layan-light global theme and GTK theme for the invoking user
  -h, --help  Show this help

Examples:
  sudo ./install.sh
  sudo ./install.sh --apply
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY_THEME=dark; shift ;;
    --apply-light) APPLY_THEME=light; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ "$EUID" -ne "$ROOT_UID" ]]; then
  echo "Error: the installer must be run as root. Run: sudo $0" >&2
  exit 1
fi

AURORAE_SYSTEM_DIR="/usr/share/aurorae/themes"
SCHEMES_DIR="/usr/share/color-schemes"
PLASMA_DIR="/usr/share/plasma/desktoptheme"
LOOKFEEL_DIR="/usr/share/plasma/look-and-feel"
KVANTUM_DIR="/usr/share/Kvantum"
WALLPAPER_DIR="/usr/share/wallpapers"
KONSOLE_DIR="/usr/share/konsole"
ICONS_DIR="/usr/share/icons"
GTK_THEMES_DIR="/usr/share/themes"

# The user who ran sudo, if any. Per-user steps (cache rebuild, applying the
# global theme) must run as them, not as root.
TARGET_USER=""
TARGET_HOME=""
if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != root ]]; then
  TARGET_USER=$SUDO_USER
  TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
fi

run_as_target_user() {
  local uid
  uid=$(id -u "$TARGET_USER")
  runuser -u "$TARGET_USER" -- env \
    HOME="$TARGET_HOME" \
    XDG_RUNTIME_DIR="/run/user/${uid}" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${uid}/bus" \
    QT_QPA_PLATFORM=offscreen \
    "$@"
}

mkdir -p "${SCHEMES_DIR}" "${PLASMA_DIR}" "${LOOKFEEL_DIR}" "${KVANTUM_DIR}" "${WALLPAPER_DIR}" "${KONSOLE_DIR}" "${ICONS_DIR}"

install() {
  local name=${1}
  local color=${2}
  local else_color=""

  [[ ${color} == '-light' ]] && else_color='Light'

  echo "Installing ${name}${color}..."

  [[ -d ${PLASMA_DIR}/${name}${color} ]] && rm -rf ${PLASMA_DIR}/${name}${color}
  [[ -f ${SCHEMES_DIR}/${name}${else_color}.colors ]] && rm -f ${SCHEMES_DIR}/${name}${else_color}.colors
  [[ -d ${LOOKFEEL_DIR}/com.github.vinceliuice.${name}${color} ]] && rm -rf ${LOOKFEEL_DIR}/com.github.vinceliuice.${name}${color}
  [[ -d ${KVANTUM_DIR}/${name} ]] && rm -rf ${KVANTUM_DIR}/${name}*
  [[ -d ${WALLPAPER_DIR}/${name}${color} ]] && rm -rf ${WALLPAPER_DIR}/${name}${color}

  cp -rf "${SRC_DIR}/color-schemes/${name}${else_color}.colors"                         "${SCHEMES_DIR}/"
  cp -rf "${SRC_DIR}/Kvantum/${name}"*                                                  "${KVANTUM_DIR}/"
  mkdir -p "${PLASMA_DIR}/${name}${color}"
  cp -rf "${SRC_DIR}/plasma/desktoptheme/common"                                        "${PLASMA_DIR}/${name}${color}/"
  cp -rf "${SRC_DIR}/plasma/desktoptheme/${name}${color}/"*                             "${PLASMA_DIR}/${name}${color}/"
  cp -rf "${SRC_DIR}/color-schemes/${name}${else_color}.colors"                         "${PLASMA_DIR}/${name}${color}/colors"
  cp -rf "${SRC_DIR}/plasma/look-and-feel/com.github.vinceliuice.${name}${color}"       "${LOOKFEEL_DIR}/"
  cp -rf "${SRC_DIR}/wallpaper/${name}${color}"                                         "${WALLPAPER_DIR}/"
}

echo "Installing '${THEME_NAME}' KDE themes (system-wide)..."
echo "Global theme packages will be installed to: ${LOOKFEEL_DIR}"

for color in "${colors[@]:-${COLOR_VARIANTS[@]}}"; do
  install "${name:-${THEME_NAME}}" "${color}"
done

# Window decorations go in the invoking user's directory, not /usr/share. The
# login screen has no windows, so it does not need them. Without a sudo user
# there is no home to install into, so fall back to the system directory.
if [[ -n "$TARGET_USER" ]]; then
  AURORAE_DIR="${TARGET_HOME}/.local/share/aurorae/themes"
  echo "Installing Aurorae themes for ${TARGET_USER} to ${AURORAE_DIR}..."
  run_as_target_user mkdir -p "${AURORAE_DIR}"
  for aurorae_src in "${SRC_DIR}/aurorae/themes/${THEME_NAME}"*; do
    aurorae_name=$(basename "${aurorae_src}")
    run_as_target_user rm -rf "${AURORAE_DIR}/${aurorae_name}"
    run_as_target_user cp -rf "${aurorae_src}" "${AURORAE_DIR}/"
    # Drop a copy left by an earlier system-wide install so it is not listed twice
    rm -rf "${AURORAE_SYSTEM_DIR:?}/${aurorae_name}"
  done
else
  AURORAE_DIR="${AURORAE_SYSTEM_DIR}"
  echo "Not run through sudo, so Aurorae themes are installed system-wide to ${AURORAE_DIR}..."
  mkdir -p "${AURORAE_DIR}"
  cp -rf "${SRC_DIR}/aurorae/themes/${THEME_NAME}"* "${AURORAE_DIR}/"
fi

echo "Installing layan cursors (dark, light and darker)..."
for cursor_theme in layan-dark-cursors layan-light-cursors layan-darker-cursors; do
  rm -rf "${ICONS_DIR}/${cursor_theme}"
  cp -rf "${SRC_DIR}/cursors/${cursor_theme}" "${ICONS_DIR}/"
done

echo "Installing Konsole color schemes and profiles..."
cp -rf "${SRC_DIR}/konsole/"* "${KONSOLE_DIR}/"

# The GTK themes import Breeze-GTK and only override its colors and corner shapes
echo "Installing GTK themes (Layan and Layan-light)..."
mkdir -p "${GTK_THEMES_DIR}"
for gtk_src in "${SRC_DIR}/gtk/themes/"*; do
  gtk_name=$(basename "${gtk_src}")
  rm -rf "${GTK_THEMES_DIR:?}/${gtk_name}"
  cp -rf "${gtk_src}" "${GTK_THEMES_DIR}/"
done
if [[ ! -d "${GTK_THEMES_DIR}/Breeze" || ! -d "${GTK_THEMES_DIR}/Breeze-Dark" ]]; then
  echo "Warning: Breeze-GTK is not installed, so the Layan GTK themes have nothing to build on." >&2
  echo "  Install the breeze-gtk package (Arch) or breeze-gtk-theme (Debian/Ubuntu/Fedora)." >&2
fi

if [[ -n "$TARGET_USER" ]] && command -v kbuildsycoca6 >/dev/null 2>&1; then
  run_as_target_user kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi

# Select the Layan GTK theme for the invoking user. kde-gtk-config's daemon owns the GTK
# settings files, so ask it to switch rather than editing them. libadwaita apps ignore the
# theme name, so also import the Layan palette from the user's GTK 4 stylesheet.
apply_gtk_theme() {
  local gtk_theme=$1
  local gtk4_dir="${TARGET_HOME}/.config/gtk-4.0"
  local palette="${GTK_THEMES_DIR}/${gtk_theme}/gtk-4.0/libadwaita.css"

  if command -v qdbus6 >/dev/null 2>&1 \
    && run_as_target_user qdbus6 org.kde.kded6 /modules/gtkconfig org.kde.GtkConfig.setGtkTheme "${gtk_theme}" >/dev/null 2>&1; then
    echo "Applied GTK theme for ${TARGET_USER}: ${gtk_theme}"
  else
    echo "Warning: could not set the GTK theme. Choose ${gtk_theme} under System Settings -> Application Style -> Configure GNOME/GTK Application Style." >&2
  fi

  run_as_target_user mkdir -p "${gtk4_dir}"
  run_as_target_user touch "${gtk4_dir}/gtk.css"
  # Drop the import of either Layan variant before adding the right one
  run_as_target_user sed -i '\#/themes/Layan[^/]*/gtk-4.0/libadwaita.css#d' "${gtk4_dir}/gtk.css"
  # kde-gtk-config writes this file without a trailing newline, so add one before appending
  run_as_target_user sh -c '
    if [ -s "$2" ] && [ -n "$(tail -c1 "$2")" ]; then echo >> "$2"; fi
    printf "@import url(\"file://%s\");\n" "$1" >> "$2"
  ' _ "${palette}" "${gtk4_dir}/gtk.css"
}

if [[ -n "$APPLY_THEME" ]]; then
  if [[ "$APPLY_THEME" == "light" ]]; then
    LOOKFEEL_ID=com.github.vinceliuice.Layan-light
    GTK_THEME_ID=Layan-light
  else
    LOOKFEEL_ID=com.github.vinceliuice.Layan
    GTK_THEME_ID=Layan
  fi

  if [[ -z "$TARGET_USER" ]]; then
    echo "Not run through sudo, so there is no user to apply the theme to. Activate it as your user with:"
    echo "  plasma-apply-lookandfeel -a ${LOOKFEEL_ID}"
  elif ! command -v plasma-apply-lookandfeel >/dev/null 2>&1; then
    echo "Warning: plasma-apply-lookandfeel not found; global theme was installed but not activated." >&2
  elif run_as_target_user plasma-apply-lookandfeel -a "${LOOKFEEL_ID}"; then
    echo "Applied global theme for ${TARGET_USER}: ${LOOKFEEL_ID}"
    apply_gtk_theme "${GTK_THEME_ID}"
  else
    echo "Warning: could not apply the global theme. Activate it as your user with:" >&2
    echo "  plasma-apply-lookandfeel -a ${LOOKFEEL_ID}" >&2
  fi
fi

echo "Install finished."
echo "Look-and-feel (Global Theme) packages:"
echo "  ${LOOKFEEL_DIR}/com.github.vinceliuice.Layan"
echo "  ${LOOKFEEL_DIR}/com.github.vinceliuice.Layan-light"
echo "Cursors (System Settings -> Cursors -> layan-dark/light/darker-cursors):"
echo "  ${ICONS_DIR}/layan-dark-cursors"
echo "  ${ICONS_DIR}/layan-light-cursors"
echo "  ${ICONS_DIR}/layan-darker-cursors"
echo "GTK themes (System Settings -> Application Style -> Configure GNOME/GTK Application Style):"
echo "  ${GTK_THEMES_DIR}/Layan"
echo "  ${GTK_THEMES_DIR}/Layan-light"
echo "Konsole (Settings -> Konsole -> Profiles -> Layan):"
echo "  ${KONSOLE_DIR}/Layan.profile + Layan.colorscheme"
echo "  ${KONSOLE_DIR}/LayanLight.profile + LayanLight.colorscheme"

if [[ -z "$APPLY_THEME" ]]; then
  echo "To activate the global theme now, run as your user:"
  echo "  plasma-apply-lookandfeel -a com.github.vinceliuice.Layan"
fi
