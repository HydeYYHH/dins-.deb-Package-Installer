# dins: .deb Package Installer

**dins** is a straightforward .deb package installer designed for non-Debian Linux users, such as those using Arch Linux. This script ensures a clean installation and uninstallation process by tracking all newly created files and directories during installation. It facilitates the removal of the application by systematically deleting all associated files.

### Available Options:

- **Install**: Use `dins install package.deb` to install a .deb package.

- **Uninstall**: Use `dins uninstall package_name` to cleanly remove a previously installed package.

- **List**: Use `dins list` to display a list of installed packages.

- **Add**: Use `dins add executable_file` to add an executable file to your `/usr/local/bin` directory.


