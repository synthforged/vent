#!/usr/bin/env bash
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────
[[ -n "${HOME:-}" ]] || { echo "ERROR: \$HOME is not set"; exit 1; }
REPO_URL="https://github.com/synthforged/vent.git"
INSTALL_DIR="$HOME/.local/share/vent"
BIN_DIR="$HOME/.local/bin"
MIN_PY_MAJOR=3
MIN_PY_MINOR=11

# ─── Output helpers ───────────────────────────────────────────────────
RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m'
BLUE='\033[0;34m' BOLD='\033[1m' NC='\033[0m'

info()  { printf "${GREEN}>>>${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}>>>${NC} %s\n" "$*"; }
die()   { printf "${RED}>>>${NC} %s\n" "$*"; exit 1; }
step()  { printf "\n${BLUE}${BOLD}==> %s${NC}\n" "$*"; }

confirm() {
    read -rp "$1 [Y/n] " ans
    [[ "${ans:-y}" =~ ^[Yy]$ ]]
}

# ─── Distro detection ────────────────────────────────────────────────

detect_distro() {
    [ "$(uname -s)" = "Linux" ] || die "vent requires Linux (Wayland)."

    DISTRO=unknown
    [ ! -f /etc/os-release ] && return
    . /etc/os-release
    case "${ID:-}" in
        arch|cachyos|endeavouros|manjaro|artix|garuda) DISTRO=arch ;;
        ubuntu|debian|pop|linuxmint|elementary|zorin)  DISTRO=debian ;;
        fedora|nobara|rhel|centos|rocky|alma)          DISTRO=fedora ;;
        *)
            case "${ID_LIKE:-}" in
                *arch*)              DISTRO=arch ;;
                *debian*|*ubuntu*)   DISTRO=debian ;;
                *fedora*|*rhel*)     DISTRO=fedora ;;
            esac ;;
    esac
}

# ─── Python detection ────────────────────────────────────────────────

find_python() {
    PYTHON=""
    for cmd in python3.13 python3.12 python3.11 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            if "$cmd" -c "import sys; exit(0 if sys.version_info >= ($MIN_PY_MAJOR,$MIN_PY_MINOR) else 1)" 2>/dev/null; then
                PYTHON="$(command -v "$cmd")"
                break
            fi
        fi
    done
    [ -n "$PYTHON" ] || die "Python >= $MIN_PY_MAJOR.$MIN_PY_MINOR not found. Please install it."
    local ver
    ver="$("$PYTHON" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')")"
    info "Found Python $ver ($PYTHON)"
}

# ─── System dependency checks ────────────────────────────────────────

# Shared array for missing packages (avoids word-splitting issues)
MISSING=()

check_missing_pacman() {
    MISSING=()
    for pkg in "$@"; do
        pacman -Qi "$pkg" &>/dev/null || MISSING+=("$pkg")
    done
}

check_missing_dpkg() {
    MISSING=()
    for pkg in "$@"; do
        dpkg -l "$pkg" 2>/dev/null | grep -q "^ii" || MISSING+=("$pkg")
    done
}

check_missing_rpm() {
    MISSING=()
    for pkg in "$@"; do
        rpm -q "$pkg" &>/dev/null || MISSING+=("$pkg")
    done
}

deps_arch() {
    local pkgs=(gtk4 gtk4-layer-shell gobject-introspection cairo portaudio wtype wl-clipboard)
    check_missing_pacman "${pkgs[@]}"
    if [ ${#MISSING[@]} -eq 0 ]; then
        info "All system packages present"
        return
    fi
    warn "Missing: ${MISSING[*]}"
    confirm "Install with pacman?" && sudo pacman -S --needed "${MISSING[@]}" \
        || die "Cannot continue without: ${MISSING[*]}"
}

deps_debian() {
    # Detect correct GI dev package name (changed across versions)
    local gi_dev="libgirepository1.0-dev"
    if apt-cache show libgirepository-2.0-dev &>/dev/null 2>&1; then
        gi_dev="libgirepository-2.0-dev"
    fi

    local core_pkgs=(
        build-essential python3-dev python3-venv pkg-config
        "$gi_dev" libcairo2-dev
        libgtk-4-dev gir1.2-gtk-4.0
        libportaudio2 portaudio19-dev
        wl-clipboard
    )
    check_missing_dpkg "${core_pkgs[@]}"
    if [ ${#MISSING[@]} -gt 0 ]; then
        warn "Missing core packages: ${MISSING[*]}"
        if confirm "Install with apt?"; then
            sudo apt-get update -qq
            sudo apt-get install -y "${MISSING[@]}"
        else
            die "Cannot continue without: ${MISSING[*]}"
        fi
    else
        info "Core packages present"
    fi

    # Wayland-specific packages (may not be in older repos)
    local need_layer_shell=false need_wtype=false
    dpkg -l libgtk4-layer-shell-dev 2>/dev/null | grep -q "^ii" || need_layer_shell=true
    command -v wtype &>/dev/null || need_wtype=true

    if $need_layer_shell; then
        if apt-cache show libgtk4-layer-shell-dev &>/dev/null 2>&1; then
            info "Installing gtk4-layer-shell..."
            sudo apt-get install -y libgtk4-layer-shell-dev
        else
            warn "gtk4-layer-shell not in repos — build from source:"
            warn "  https://github.com/wmww/gtk4-layer-shell"
        fi
    fi
    if $need_wtype; then
        if apt-cache show wtype &>/dev/null 2>&1; then
            info "Installing wtype..."
            sudo apt-get install -y wtype
        else
            warn "wtype not in repos — build from source:"
            warn "  https://github.com/atx/wtype"
        fi
    fi
}

deps_fedora() {
    local pkgs=(
        gtk4-devel gobject-introspection-devel cairo-devel
        python3-devel gcc pkg-config
        portaudio-devel wl-clipboard
    )
    check_missing_rpm "${pkgs[@]}"
    if [ ${#MISSING[@]} -gt 0 ]; then
        warn "Missing: ${MISSING[*]}"
        confirm "Install with dnf?" && sudo dnf install -y "${MISSING[@]}" \
            || die "Cannot continue without: ${MISSING[*]}"
    else
        info "Core packages present"
    fi

    # Wayland extras
    rpm -q gtk4-layer-shell-devel &>/dev/null \
        || sudo dnf install -y gtk4-layer-shell-devel 2>/dev/null \
        || warn "gtk4-layer-shell-devel not in repos — build from source"
    command -v wtype &>/dev/null \
        || sudo dnf install -y wtype 2>/dev/null \
        || warn "wtype not in repos — build from source"
}

deps_unknown() {
    warn "Unrecognized Linux distribution."
    warn "Ensure the following are installed before continuing:"
    warn "  - GTK4 (with GObject Introspection typelibs)"
    warn "  - gtk4-layer-shell"
    warn "  - GObject Introspection + Cairo dev headers"
    warn "  - PortAudio"
    warn "  - wtype, wl-clipboard"
    warn "  - pkg-config, C compiler"
    echo
    confirm "Continue anyway?" || exit 1
}

# ─── Source resolution ────────────────────────────────────────────────

get_source_dir() {
    # If running from the repo, use it directly
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || script_dir=""
    if [ -n "$script_dir" ] && [ -f "$script_dir/pyproject.toml" ]; then
        SOURCE_DIR="$script_dir"
        return
    fi

    # Otherwise clone to a temp dir (curl | bash case)
    command -v git &>/dev/null || die "git is required to download vent."
    CLONE_DIR="$(mktemp -d)"
    trap 'rm -rf "$CLONE_DIR"' EXIT
    info "Cloning vent..."
    git clone --depth 1 "$REPO_URL" "$CLONE_DIR" 2>&1 | tail -1
    SOURCE_DIR="$CLONE_DIR"
}

# ─── Install ─────────────────────────────────────────────────────────

do_install() {
    if [ -d "$INSTALL_DIR" ]; then
        warn "Existing install at $INSTALL_DIR"
        confirm "Remove and reinstall?" || die "Aborted."
        rm -rf "$INSTALL_DIR"
    fi

    info "Creating venv at $INSTALL_DIR"
    "$PYTHON" -m venv "$INSTALL_DIR"

    info "Installing vent and Python dependencies..."
    "$INSTALL_DIR/bin/pip" install --upgrade pip -q
    "$INSTALL_DIR/bin/pip" install "$SOURCE_DIR"

    mkdir -p "$BIN_DIR"
    cat > "$BIN_DIR/vent" << EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/bin/vent" "\$@"
EOF
    chmod +x "$BIN_DIR/vent"
    info "Executable: $BIN_DIR/vent"
}

# ─── PATH setup ──────────────────────────────────────────────────────

ensure_path() {
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        info "$BIN_DIR already in PATH"
        return
    fi

    warn "$BIN_DIR is not in your PATH"
    local rc=""
    case "$(basename "${SHELL:-bash}")" in
        zsh)  rc="$HOME/.zshrc" ;;
        bash) rc="$HOME/.bashrc" ;;
        fish) rc="$HOME/.config/fish/config.fish" ;;
    esac

    if [ -n "$rc" ] && [ -f "$rc" ]; then
        if confirm "Add $BIN_DIR to PATH in $rc?"; then
            if [[ "$rc" == *fish* ]]; then
                echo "fish_add_path $BIN_DIR" >> "$rc"
            else
                printf '\nexport PATH="%s:$PATH"\n' "$BIN_DIR" >> "$rc"
            fi
            info "Added to $rc — restart your shell or: source $rc"
            return
        fi
    fi
    warn "Add manually to your shell config:"
    warn "  export PATH=\"$BIN_DIR:\$PATH\""
}

# ─── Main ─────────────────────────────────────────────────────────────

main() {
    printf "${BOLD}vent installer${NC}\n\n"

    step "Detecting platform"
    detect_distro
    info "Detected: Linux ($DISTRO)"

    step "Checking Python"
    find_python

    step "System dependencies"
    case "$DISTRO" in
        arch)    deps_arch ;;
        debian)  deps_debian ;;
        fedora)  deps_fedora ;;
        *)       deps_unknown ;;
    esac

    step "Fetching source"
    get_source_dir
    info "Source: $SOURCE_DIR"

    step "Installing vent"
    do_install

    step "Configuring PATH"
    ensure_path

    echo
    info "Done! Run 'vent' to start."
    info "To uninstall: rm -rf \"$INSTALL_DIR\" \"$BIN_DIR/vent\""
}

main "$@"
