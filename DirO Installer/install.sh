#!/bin/bash

# Define directories
INSTALL_DIR="$HOME/DirO"
APP_DESKTOP_FILE="$HOME/.local/share/applications/DirO.desktop"
DESKTOP_DIR="$HOME/Desktop"
DESKTOP_SHORTCUT="$DESKTOP_DIR/DirO.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

# Check for Desktop directory (some distros use lowercase 'desktop')
if [ ! -d "$DESKTOP_DIR" ] && [ -d "$HOME/desktop" ]; then
    DESKTOP_DIR="$HOME/desktop"
    DESKTOP_SHORTCUT="$DESKTOP_DIR/DirO.desktop"
fi

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$DESKTOP_DIR"

# Move files to installation directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
if [ ! -f "$SCRIPT_DIR/DirO" ] || [ ! -f "$SCRIPT_DIR/DirO.png" ]; then
    echo "Error: DirO or DirO.png missing!"
    exit 1
fi
mv "$SCRIPT_DIR/DirO" "$INSTALL_DIR/DirO"
mv "$SCRIPT_DIR/DirO.png" "$INSTALL_DIR/DirO.png"

# Set permissions
chmod +x "$INSTALL_DIR/DirO"
chmod 644 "$INSTALL_DIR/DirO.png"

# Create .desktop file for application menu
cat > "$APP_DESKTOP_FILE" << EOL
[Desktop Entry]
Name=DirO
Comment=File Explorer and Organizer
Exec=$INSTALL_DIR/DirO
Icon=$INSTALL_DIR/DirO.png
Terminal=false
Type=Application
Categories=Utility;FileTools;
StartupNotify=true
EOL

# Create .desktop file for desktop shortcut
cat > "$DESKTOP_SHORTCUT" << EOL
[Desktop Entry]
Name=DirO
Comment=File Explorer and Organizer
Exec=$INSTALL_DIR/DirO
Icon=$INSTALL_DIR/DirO.png
Terminal=false
Type=Application
StartupNotify=true
EOL

# Set permissions for .desktop files
chmod 644 "$APP_DESKTOP_FILE"
chmod +x "$DESKTOP_SHORTCUT"

# Update desktop and icon caches
update-desktop-database ~/.local/share/applications/ || echo "Failed to update desktop database, may need manual refresh"
gtk-update-icon-cache ~/.local/share/icons/hicolor/ || echo "Failed to update icon cache, may need manual refresh"

echo "Installation complete!"
echo "Find 'DirO' in your application menu and on your Desktop."
echo "If the icon doesn’t appear, try logging out and back in or rebooting."
