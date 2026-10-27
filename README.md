# Laptop LiveCam — Windows

Windows port, in Rust. Early: it builds, there is an MSI target, and no
installer has been published yet.

```
windows/                 the Rust crate
windows/packaging/       WiX source and build-msi.ps1
```

Build needs the Rust toolchain and WiX on a Windows host:

```powershell
cd windows
cargo build --release
.\packaging\build-msi.ps1
```

For a working camera today, use the Linux or macOS build from
[Releases](https://github.com/thefangeddeity/laptop-livecam/releases/latest).
The `main` branch is the Linux lineage; `macos` is the Mac one.
