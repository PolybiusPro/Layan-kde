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
look-and-feel / global theme, Konsole, Aurorae, Kvantum, cursors, wallpapers)
for all users under /usr/share. Must be run as root, so the login screen
(which runs as its own user) can see the theme too.

Options:
  --apply     Activate the dark Layan global theme for the invoking user
  --apply-light
              Activate the Layan-light global theme for the invoking user
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

AURORAE_DIR="/usr/share/aurorae/themes"
SCHEMES_DIR="/usr/share/color-schemes"
PLASMA_DIR="/usr/share/plasma/desktoptheme"
LOOKFEEL_DIR="/usr/share/plasma/look-and-feel"
KVANTUM_DIR="/usr/share/Kvantum"
WALLPAPER_DIR="/usr/share/wallpapers"
KONSOLE_DIR="/usr/share/konsole"
ICONS_DIR="/usr/share/icons"

# The user who ran sudo, if any. Per-user steps (cache rebuild, applying the
# global theme) must run as them, not as root.
TARGET_USER=""
if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != root ]]; then
  TARGET_USER=$SUDO_USER
fi

run_as_target_user() {
  local uid home
  uid=$(id -u "$TARGET_USER")
  home=$(getent passwd "$TARGET_USER" | cut -d: -f6)
  runuser -u "$TARGET_USER" -- env \
    HOME="$home" \
    XDG_RUNTIME_DIR="/run/user/${uid}" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${uid}/bus" \
    QT_QPA_PLATFORM=offscreen \
    "$@"
}

mkdir -p "${AURORAE_DIR}" "${SCHEMES_DIR}" "${PLASMA_DIR}" "${LOOKFEEL_DIR}" "${KVANTUM_DIR}" "${WALLPAPER_DIR}" "${KONSOLE_DIR}" "${ICONS_DIR}"

install() {
  local name=${1}
  local color=${2}
  local else_color=""

  [[ ${color} == '-light' ]] && else_color='Light'

  echo "Installing ${name}${color}..."

  [[ -d ${AURORAE_DIR}/${name}${color} ]] && rm -rf ${AURORAE_DIR}/${name}*
  [[ -d ${PLASMA_DIR}/${name}${color} ]] && rm -rf ${PLASMA_DIR}/${name}${color}
  [[ -f ${SCHEMES_DIR}/${name}${else_color}.colors ]] && rm -f ${SCHEMES_DIR}/${name}${else_color}.colors
  [[ -d ${LOOKFEEL_DIR}/com.github.vinceliuice.${name}${color} ]] && rm -rf ${LOOKFEEL_DIR}/com.github.vinceliuice.${name}${color}
  [[ -d ${KVANTUM_DIR}/${name} ]] && rm -rf ${KVANTUM_DIR}/${name}*
  [[ -d ${WALLPAPER_DIR}/${name}${color} ]] && rm -rf ${WALLPAPER_DIR}/${name}${color}

  cp -rf "${SRC_DIR}/aurorae/themes/${name}"*                                           "${AURORAE_DIR}/"
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

echo "Installing layan cursors (dark, light and darker)..."
for cursor_theme in layan-dark-cursors layan-light-cursors layan-darker-cursors; do
  rm -rf "${ICONS_DIR}/${cursor_theme}"
  cp -rf "${SRC_DIR}/cursors/${cursor_theme}" "${ICONS_DIR}/"
done

echo "Installing Konsole color schemes and profiles..."
cp -rf "${SRC_DIR}/konsole/"* "${KONSOLE_DIR}/"

if [[ -n "$TARGET_USER" ]] && command -v kbuildsycoca6 >/dev/null 2>&1; then
  run_as_target_user kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi

if [[ -n "$APPLY_THEME" ]]; then
  if [[ "$APPLY_THEME" == "light" ]]; then
    LOOKFEEL_ID=com.github.vinceliuice.Layan-light
  else
    LOOKFEEL_ID=com.github.vinceliuice.Layan
  fi

  if [[ -z "$TARGET_USER" ]]; then
    echo "Not run through sudo, so there is no user to apply the theme to. Activate it as your user with:"
    echo "  plasma-apply-lookandfeel -a ${LOOKFEEL_ID}"
  elif ! command -v plasma-apply-lookandfeel >/dev/null 2>&1; then
    echo "Warning: plasma-apply-lookandfeel not found; global theme was installed but not activated." >&2
  elif run_as_target_user plasma-apply-lookandfeel -a "${LOOKFEEL_ID}"; then
    echo "Applied global theme for ${TARGET_USER}: ${LOOKFEEL_ID}"
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
echo "Konsole (Settings -> Konsole -> Profiles -> Layan):"
echo "  ${KONSOLE_DIR}/Layan.profile + Layan.colorscheme"
echo "  ${KONSOLE_DIR}/LayanLight.profile + LayanLight.colorscheme"

if [[ -z "$APPLY_THEME" ]]; then
  echo "To activate the global theme now, run as your user:"
  echo "  plasma-apply-lookandfeel -a com.github.vinceliuice.Layan"
fi
