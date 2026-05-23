#!/bin/bash
set -euo pipefail

ROOT_UID=0
SRC_DIR=$(cd "$(dirname "$0")" && pwd)

THEME_NAME=Layan
COLOR_VARIANTS=('' '-light')
APPLY_THEME=""
INSTALL_SCOPE=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install Layan KDE theme components (Plasma desktop theme, color scheme,
look-and-feel / global theme, Konsole, Aurorae, Kvantum, wallpapers).

Options:
  --system    Install for all users under /usr/share (requires root)
  --user      Install for the current user under ~/.local (default)
  --apply     Activate the dark Layan global theme after installing
  --apply-light
              Activate the Layan-light global theme after installing
  -h, --help  Show this help

Examples:
  ./install.sh
  sudo ./install.sh --system
  ./install.sh --apply
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --system) INSTALL_SCOPE=system; shift ;;
    --user) INSTALL_SCOPE=user; shift ;;
    --apply) APPLY_THEME=dark; shift ;;
    --apply-light) APPLY_THEME=light; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$INSTALL_SCOPE" ]]; then
  if [[ "$EUID" -eq "$ROOT_UID" ]]; then
    INSTALL_SCOPE=system
  else
    INSTALL_SCOPE=user
  fi
fi

if [[ "$INSTALL_SCOPE" == "system" ]]; then
  if [[ "$EUID" -ne "$ROOT_UID" ]]; then
    echo "Error: system-wide install requires root. Run: sudo $0 --system" >&2
    exit 1
  fi
  AURORAE_DIR="/usr/share/aurorae/themes"
  SCHEMES_DIR="/usr/share/color-schemes"
  PLASMA_DIR="/usr/share/plasma/desktoptheme"
  LOOKFEEL_DIR="/usr/share/plasma/look-and-feel"
  KVANTUM_DIR="/usr/share/Kvantum"
  WALLPAPER_DIR="/usr/share/wallpapers"
  KONSOLE_DIR="/usr/share/konsole"
else
  AURORAE_DIR="${HOME}/.local/share/aurorae/themes"
  SCHEMES_DIR="${HOME}/.local/share/color-schemes"
  PLASMA_DIR="${HOME}/.local/share/plasma/desktoptheme"
  LOOKFEEL_DIR="${HOME}/.local/share/plasma/look-and-feel"
  KVANTUM_DIR="${HOME}/.config/Kvantum"
  WALLPAPER_DIR="${HOME}/.local/share/wallpapers"
  KONSOLE_DIR="${HOME}/.local/share/konsole"
fi

mkdir -p "${AURORAE_DIR}" "${SCHEMES_DIR}" "${PLASMA_DIR}" "${LOOKFEEL_DIR}" "${KVANTUM_DIR}" "${WALLPAPER_DIR}" "${KONSOLE_DIR}"

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

echo "Installing '${THEME_NAME}' KDE themes (${INSTALL_SCOPE}-wide)..."
echo "Global theme packages will be installed to: ${LOOKFEEL_DIR}"

for color in "${colors[@]:-${COLOR_VARIANTS[@]}}"; do
  install "${name:-${THEME_NAME}}" "${color}"
done

echo "Installing Konsole color schemes and profiles..."
cp -rf "${SRC_DIR}/konsole/"* "${KONSOLE_DIR}/"

if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi

if [[ -n "$APPLY_THEME" ]]; then
  if ! command -v plasma-apply-lookandfeel >/dev/null 2>&1; then
    echo "Warning: plasma-apply-lookandfeel not found; global theme was installed but not activated." >&2
  elif [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    echo "Global theme installed. Activate it after login with:"
    if [[ "$APPLY_THEME" == "light" ]]; then
      echo "  plasma-apply-lookandfeel -a com.github.vinceliuice.Layan-light"
    else
      echo "  plasma-apply-lookandfeel -a com.github.vinceliuice.Layan"
    fi
  else
    if [[ "$APPLY_THEME" == "light" ]]; then
      plasma-apply-lookandfeel -a com.github.vinceliuice.Layan-light
      echo "Applied global theme: com.github.vinceliuice.Layan-light"
    else
      plasma-apply-lookandfeel -a com.github.vinceliuice.Layan
      echo "Applied global theme: com.github.vinceliuice.Layan"
    fi
  fi
fi

echo "Install finished."
echo "Look-and-feel (Global Theme) packages:"
echo "  ${LOOKFEEL_DIR}/com.github.vinceliuice.Layan"
echo "  ${LOOKFEEL_DIR}/com.github.vinceliuice.Layan-light"
echo "Konsole (Settings -> Konsole -> Profiles -> Layan):"
echo "  ${KONSOLE_DIR}/Layan.profile + Layan.colorscheme"
echo "  ${KONSOLE_DIR}/LayanLight.profile + LayanLight.colorscheme"

if [[ "$INSTALL_SCOPE" == "user" && -d "/usr/share/plasma/look-and-feel/com.github.vinceliuice.Layan" ]]; then
  echo "Warning: Layan is also installed under /usr/share. Duplicate Global Theme and"
  echo "Splash entries can appear in System Settings. Use one install location only:"
  echo "  sudo $0 --system    # system-wide (removes ~/.local look-and-feel duplicates)"
  echo "  or: sudo rm -rf /usr/share/plasma/look-and-feel/com.github.vinceliuice.Layan*"
fi

if [[ "$INSTALL_SCOPE" == "system" ]]; then
  rm -rf "${HOME}/.local/share/plasma/look-and-feel/com.github.vinceliuice.Layan" \
         "${HOME}/.local/share/plasma/look-and-feel/com.github.vinceliuice.Layan-light"
  echo "Removed user-local look-and-feel copies to avoid duplicate Settings entries."
fi

if [[ -z "$APPLY_THEME" ]]; then
  echo "To activate the global theme now, run:"
  echo "  plasma-apply-lookandfeel -a com.github.vinceliuice.Layan"
fi
