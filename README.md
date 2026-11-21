# NonGKI_FinaSU_OnePlus9R

Automated Non-GKI kernel builds for the OnePlus 9R (`lemonades`), with **FinaSU** (built-in) and **SUSFS** integrated into the kernel.

Based on the build flow of [NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd), trimmed down to a single device.

中文说明: [README_CN.md](README_CN.md)

## Specs

| Item | Value |
| --- | --- |
| Device | OnePlus 9R (`lemonades`) |
| Kernel source | [wcedla/android_kernel_oneplus_sm8250_los](https://github.com/wcedla/android_kernel_oneplus_sm8250_los) (`lineage-22.1`) |
| Kernel version | 4.19.325 |
| ROM | LineageOS 22.1 / Android 15 (AOSP-based 4.19 kona kernels) |
| Root | [FinaSU](https://github.com/LyraVoid/FinaSU) `v1.6.5` (built-in, `CONFIG_KSU=y`) |
| Hook | Tracepoint |
| SUSFS | v2.4.0 |
| Packaging | AnyKernel3 |
| Defconfig | `vendor/kona-perf_defconfig` |

## Usage

1. Fork this repository (or use it directly).
2. **Actions** → **Build OnePlus 9R (LineageOS 22.1 A15)** → **Run workflow**.
3. Download `lemonades-lineageos22_a15-*-AnyKernel3.zip` and flash it with a recovery or kernel manager.
4. Install the bundled `FinaSU-manager.apk` to manage root.

A weekly scheduled build runs every Friday at 18:00 UTC.

## Notes

- FinaSU is compiled into the image (`CONFIG_KSU=y`). The manager signing certificate is aligned automatically through `KSU_EXPECTED_SIZE2 / KSU_EXPECTED_HASH2 / KSU_SECOND_SIGNATURE_RELEASE=1`.
- SUSFS applies the generic 4.19 patch plus `kona_cos15_a15/susfs_fixed` from NonGKI_Kernel_Patches.
- When a build fails, rejects and error logs are uploaded as artifacts (`BUILD_DEBUGGER=true`).
- Flash at your own risk; back up your boot partition first.

## Credits

- [NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) — build flow
- [NonGKI_Kernel_Patches](https://github.com/JackA1ltman/NonGKI_Kernel_Patches) — SUSFS fixed patches
- [FinaSU](https://github.com/LyraVoid/FinaSU) — root solution
- [SUSFS](https://gitlab.com/simonpunk/susfs4ksu) — @simonpunk
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3) — @osm0sis

## License

[GPLv3](LICENSE)
