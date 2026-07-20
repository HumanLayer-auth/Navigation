# objective_c SDKROOT patch

This directory vendors `objective_c 9.4.1` from the official
[`dart-lang/native`](https://github.com/dart-lang/native/tree/main/pkgs/objective_c)
repository under its original BSD-3-Clause license.

The only behavioral change is in `hook/build.dart`:

- use an existing absolute `SDKROOT` directly;
- resolve Xcode SDK aliases such as `iphoneos` and `iphoneos26.5` beneath the
  active `DEVELOPER_DIR`;
- derive `DEVELOPER_DIR` from the compiler path supplied by Flutter when Xcode
  does not export it;
- fall back to `xcrun` with a useful error instead of throwing `Bad state: No
  element` for empty output.

`client/pubspec.yaml` pins this package with `dependency_overrides`, so the fix
is reproducible for local builds and CI and never mutates the global Pub cache.

When an official `objective_c` release contains equivalent SDK resolution,
remove this directory and the override, run `flutter pub get`, and verify an
iOS release build.
