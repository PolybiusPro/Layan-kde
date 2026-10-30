#!/bin/bash

ROOT_UID=0

if [ "$EUID" -ne "$ROOT_UID" ]; then
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

SRC_DIR=$(cd $(dirname $0) && pwd)

THEME_NAME=Layan
COLOR_VARIANTS=('' '-light')

uninstall() {
  local name=${1}
  local color=${2}

  [[ ${color} == '-light' ]] && local ELSE_COLOR='Light'

  [[ -d ${AURORAE_DIR}/${name}${color} ]] && rm -rfv ${AURORAE_DIR}/${name}*
  [[ -d ${PLASMA_DIR}/${name}${color} ]] && rm -rfv ${PLASMA_DIR}/${name}${color}
  [[ -f ${SCHEMES_DIR}/${name}${ELSE_COLOR}.colors ]] && rm -rfv ${SCHEMES_DIR}/${name}${ELSE_COLOR}.colors
  [[ -d ${LOOKFEEL_DIR}/com.github.vinceliuice.${name}${color} ]] && rm -rfv ${LOOKFEEL_DIR}/com.github.vinceliuice.${name}${color}
  [[ -d ${KVANTUM_DIR}/${name} ]] && rm -rfv ${KVANTUM_DIR}/${name}*
  [[ -d ${WALLPAPER_DIR}/${name}${color} ]] && rm -rfv ${WALLPAPER_DIR}/${name}${color}
}

echo "Uninstalling '${THEME_NAME} kde themes'..."

for color in "${colors[@]:-${COLOR_VARIANTS[@]}}"; do
  uninstall "${name:-${THEME_NAME}}" "${color}"
done

rm -rfv "${ICONS_DIR}/layan-dark-cursors" "${ICONS_DIR}/layan-light-cursors" "${ICONS_DIR}/layan-darker-cursors"

rm -fv "${KONSOLE_DIR}/Layan.colorscheme" \
      "${KONSOLE_DIR}/LayanLight.colorscheme" \
      "${KONSOLE_DIR}/Layan.profile" \
      "${KONSOLE_DIR}/LayanLight.profile" \
      "${KONSOLE_DIR}/Layan.colors" \
      "${KONSOLE_DIR}/LayanLight.colors" 2>/dev/null || true

echo "Uninstall finished..."
