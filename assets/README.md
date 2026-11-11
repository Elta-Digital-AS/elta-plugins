# Elta logo

`elta-logo.svg` is the existing Elta application's green favicon, copied without
artwork changes. `elta-logo.png` is its 512 × 512 PNG export, shared by the native
Codex and Claude packages. The PNG contains the rendered letters so the clients
do not need the source font.

Reproduce the export on macOS:

```sh
sips -s format png --resampleHeightWidth 512 512 assets/elta-logo.svg --out assets/elta-logo.png
```
