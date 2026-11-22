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

The kernel has booted on a OnePlus 9R (LE2100). With the [v5 test build](https://github.com/muling0721/NonGKI_FinaSU_OnePlus9R/actions/runs/44993917618), the Manager received a driver FD and read version `33213`; that fix is still on the test branch. **A working root shell and SUSFS behavior have not been verified.**

The v5 diagnostics show that FinaSU appended its `init.rc` fragment in full, but did not observe the `ksud` boot-completed event. The `su` hook returned `ENOENT` opening `/data/adb/ksud`, before executing it or installing a session FD. This establishes that Android could not resolve the path at the time, not whether the file exists in recovery. The Manager's bundled `libksud.so` is a separate path: its child did not obtain a driver FD, and seccomp blocked its fallback call.

The FinaSU v1.6.5 [built-in installation guide](https://github.com/LyraVoid/FinaSU/blob/f96445f9/website/docs/guide/install/built-in.md) notes that AnyKernel3 does not automatically update `ksud`. On launch, the upstream Manager attempts installation if it is recognized and the UAPI matches. Its bundled `libksud.so` can request a root shell from this driver without another root solution or a preexisting `/data/adb/ksud`.

**v6 test candidate (not device-verified):** Keeps the v5 diagnostics. Only the signature-recognized User 0 Manager receives an ordinary `O_CLOEXEC` driver FD after a successful exec of the official APK's ARM64 `libksud.so`, with location, size, and SHA-256 checked. Existing ioctl authorization, seccomp, SELinux, and Manager signature checks are unchanged. The test does not change recovery or write to `/data` itself. Verify `fina_9r_ksud_fd: payload_rc=0 fd_rc=0`, the Manager's install result, the root shell UID, daemon startup after reboot, and SUSFS behavior separately.

## Credits

- [NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) — build flow
- [NonGKI_Kernel_Patches](https://github.com/JackA1ltman/NonGKI_Kernel_Patches) — SUSFS fixed patches
- [FinaSU](https://github.com/LyraVoid/FinaSU) — root solution
- [SUSFS](https://gitlab.com/simonpunk/susfs4ksu) — @simonpunk
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3) — @osm0sis

## License

[GPLv3](LICENSE)
