#!/bin/bash
set -euo pipefail

ROOT_UID=0

if [[ "$EUID" -ne "$ROOT_UID" ]]; then
  echo "Error: the uninstaller must be run as root. Run: sudo $0" >&2
  exit 1
fi

# Destination directory
AURORAE_DIR="/usr/share/aurorae/themes"
SCHEMES_DIR="/usr/share/color-schemes"
PLASMA_DIR="/usr/share/plasma/desktoptheme"
LOOKFEEL_DIR="/usr/share/plasma/look-and-feel"
KVANTUM_DIR="/usr/share/Kvantum"
WALLPAPER_DIR="/usr/share/wallpapers"
KONSOLE_DIR="/usr/share/konsole"
ICONS_DIR="/usr/share/icons"
GTK_THEMES_DIR="/usr/share/themes"

THEME_NAME=Layan
COLOR_VARIANTS=('' '-light')

uninstall() {
  local name=${1}
  local color=${2}
  local else_color=""

  [[ ${color} == '-light' ]] && else_color='Light'

  # rm -f ignores anything that is not installed, and the globs also catch the
  # -solid and Kvantum variants
  rm -rfv "${AURORAE_DIR}/${name}"*
  rm -rfv "${PLASMA_DIR}/${name}${color}"
  rm -fv "${SCHEMES_DIR}/${name}${else_color}.colors"
  rm -rfv "${LOOKFEEL_DIR}/com.github.vinceliuice.${name}${color}"
  rm -rfv "${KVANTUM_DIR}/${name}"*
  rm -rfv "${WALLPAPER_DIR}/${name}${color}"
}

echo "Uninstalling '${THEME_NAME} kde themes'..."

for color in "${colors[@]:-${COLOR_VARIANTS[@]}}"; do
  uninstall "${name:-${THEME_NAME}}" "${color}"
done

# The installer puts Aurorae themes in the invoking user's directory
if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != root ]]; then
  user_home=$(getent passwd "$SUDO_USER" | cut -d: -f6)
  rm -rfv "${user_home}/.local/share/aurorae/themes/${THEME_NAME}"*

  # Remove the libadwaita palette import that --apply added to the user's GTK 4 stylesheet
  gtk4_css="${user_home}/.config/gtk-4.0/gtk.css"
  if [[ -f "$gtk4_css" ]]; then
    sed -i '\#/themes/Layan[^/]*/gtk-4.0/libadwaita.css#d' "$gtk4_css"
  fi
fi

rm -rfv "${GTK_THEMES_DIR}/${THEME_NAME}" "${GTK_THEMES_DIR}/${THEME_NAME}-light"

rm -rfv "${ICONS_DIR}/layan-dark-cursors" "${ICONS_DIR}/layan-light-cursors" "${ICONS_DIR}/layan-darker-cursors"

rm -fv "${KONSOLE_DIR}/Layan.colorscheme" \
      "${KONSOLE_DIR}/LayanLight.colorscheme" \
      "${KONSOLE_DIR}/Layan.profile" \
      "${KONSOLE_DIR}/LayanLight.profile" \
      "${KONSOLE_DIR}/Layan.colors" \
      "${KONSOLE_DIR}/LayanLight.colors"

echo "Uninstall finished..."
