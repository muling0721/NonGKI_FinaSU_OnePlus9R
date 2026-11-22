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
| ROM used for device testing | ColorOS 15 port (`lineage-22.1` is the kernel source branch) |
| Root | [FinaSU](https://github.com/LyraVoid/FinaSU) `v1.6.5` (built-in, `CONFIG_KSU=y`) |
| Hook | Tracepoint |
| SUSFS | v2.4.0 |
| Packaging | AnyKernel3 |
| Defconfig | `vendor/kona-perf_defconfig` |

## Usage

1. Fork this repository (or use it directly).
2. **Actions** → **Build OnePlus 9R (LineageOS 22.1 A15)** → **Run workflow**.
3. After a successful run, download `lemonades-lineageos22_a15-*-AnyKernel3.zip` and `FinaSU-manager.apk` from the run's artifacts. Select `release` only if you intend to publish a GitHub Release.

Builds run on GitHub Actions (`ubuntu-24.04`), including the weekly Friday 18:00 UTC build. Scheduled runs do not publish Releases.

## Notes

- FinaSU is compiled into the image (`CONFIG_KSU=y`). The manager signing certificate is aligned automatically through `KSU_EXPECTED_SIZE2 / KSU_EXPECTED_HASH2 / KSU_SECOND_SIGNATURE_RELEASE=1`.
- SUSFS applies the generic 4.19 patch plus [`Patches/OnePlus9R/susfs_fixed.patch`](Patches/OnePlus9R/susfs_fixed.patch).
- The AnyKernel3 installer checks for `lemonades`. This ZIP does not install or update `/data/adb/ksud`; flashing the kernel alone does not complete the root installation.
- When a build fails, rejects and error logs are uploaded as artifacts (`BUILD_DEBUGGER=true`).
- Before flashing, confirm TWRP can restore a Boot backup for the current slot, and keep the original ROM's `boot.img` if available.

## Device validation

The kernel has booted on a OnePlus 9R (LE2100). With the [v4 test build](https://github.com/muling0721/NonGKI_FinaSU_OnePlus9R/actions/runs/44991678924), the Manager read driver version `33213`; that fix is still on the test branch. **A working root shell and SUSFS behavior have not been verified.**

The v4 report shows that the Manager's `ksud` child did not obtain a driver FD and its fallback to `su` on `PATH` failed. The report does not establish whether `/data/adb/ksud` exists. The FinaSU v1.6.5 [built-in installation guide](https://github.com/LyraVoid/FinaSU/blob/f96445f9/website/docs/guide/install/built-in.md) also notes that AnyKernel3 does not automatically update `ksud`. A first-install path for this device that does not depend on existing root has not been verified.

## Credits

- [NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) — build flow
- [NonGKI_Kernel_Patches](https://github.com/JackA1ltman/NonGKI_Kernel_Patches) — SUSFS fixed patches
- [FinaSU](https://github.com/LyraVoid/FinaSU) — root solution
- [SUSFS](https://gitlab.com/simonpunk/susfs4ksu) — @simonpunk
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3) — @osm0sis

## License

[GPLv3](LICENSE)
