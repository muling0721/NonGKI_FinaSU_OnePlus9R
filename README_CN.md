# NonGKI_FinaSU_OnePlus9R

一加 9R（`lemonades`）Non-GKI 内核自动构建仓库。

基于 [NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) 的构建流程，
只保留一加 9R 的构建配置，内核内集成 **FinaSU**（内置）+ **SUSFS**。

## 信息

| 项目 | 值 |
| --- | --- |
| 机型 | OnePlus 9R（`lemonades`） |
| 内核源码 | [wcedla/android_kernel_oneplus_sm8250_los](https://github.com/wcedla/android_kernel_oneplus_sm8250_los)（`lineage-22.1`） |
| 内核版本 | 4.19.325 |
| 实机测试系统 | ColorOS 15 移植版（`lineage-22.1` 是内核源码分支） |
| Root 方案 | [FinaSU](https://github.com/LyraVoid/FinaSU) `v1.6.5`（`CONFIG_KSU=y` 内置） |
| Hook | Tracepoint |
| SUSFS | v2.4.0 |
| 打包 | AnyKernel3 |
| Defconfig | `vendor/kona-perf_defconfig` |

## 使用

1. Fork 或直接使用本仓库。
2. 打开 **Actions** → **Build OnePlus 9R (LineageOS 22.1 A15)** → **Run workflow**。
3. 构建成功后，在该次运行的 Artifacts 中下载 `lemonades-lineageos22_a15-*-AnyKernel3.zip` 和 `FinaSU-manager.apk`。仅在需要公开发布时勾选 `release`。

所有构建都在 GitHub Actions（`ubuntu-24.04`）上运行。每周五 18:00 (UTC) 定时构建，不自动发布 Release。

## 说明

- 内核以 **Built-In（`CONFIG_KSU=y`）** 方式集成 FinaSU；管理器签名通过
  `KSU_EXPECTED_SIZE2 / KSU_EXPECTED_HASH2 / KSU_SECOND_SIGNATURE_RELEASE=1`
  与 Release APK 的签名证书对齐（由 `finasu-manager` action 自动完成）。
- SUSFS 使用 4.19 通用补丁及本仓库的 [`Patches/OnePlus9R/susfs_fixed.patch`](Patches/OnePlus9R/susfs_fixed.patch)。
- AnyKernel3 安装脚本会检查设备代号 `lemonades`。本仓库的 ZIP 不会安装或更新 `/data/adb/ksud`，因此刷内核不等于完成 Root 安装。
- 构建失败时会把 `.rej` 与错误日志打进 Artifact（`BUILD_DEBUGGER=true`）。
- 刷机有风险，请先确认当前槽位的 Boot 备份可在 TWRP 恢复，并保留原 ROM 的 `boot.img`（如有）。

## 实机验证状态

一加 9R（LE2100）已验证启动。[v4 测试构建](https://github.com/muling0721/NonGKI_FinaSU_OnePlus9R/actions/runs/44991678924) 上，管理器已能读取内核驱动版本 `33213`；这项修复仍在测试分支。**Root Shell 和 SUSFS 实际功能尚未验证通过。**

v4 报告显示，管理器启动的 `ksud` 子进程未取得驱动 FD，按 `PATH` 查找的 `su` 也未成功。报告不能确认 `/data/adb/ksud` 是否存在。FinaSU v1.6.5 的 [Built-In 安装说明](https://github.com/LyraVoid/FinaSU/blob/f96445f9/website/docs/guide/install/built-in.md) 也注明 AnyKernel3 不会自动更新 `ksud`；本项目还没有验证适用于这台设备、无需现有 Root 的首次安装流程。

## 目录

```
.github/workflows/
├── build-oneplus9r-lineageos22-a15.yml   # 唯一构建入口
├── build-env/                            # 编译环境
├── build-ready/                          # 拉取内核、工具链、FinaSU
├── finasu-manager/                       # 下载 FinaSU 管理器并对齐签名
├── patch-susfs/                          # SUSFS 补丁
├── build-process/                        # 编译
├── pack-process/                         # AnyKernel3 打包
└── upload-files/                         # 上传产物
Bin/                                      # 构建脚本
Patches/                                  # SUSFS 等内核补丁
```

## 致谢

- [NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) - 构建流程
- [NonGKI_Kernel_Patches](https://github.com/JackA1ltman/NonGKI_Kernel_Patches) - SUSFS 修正补丁
- [FinaSU](https://github.com/LyraVoid/FinaSU) - 内置 Root 方案
- [SUSFS](https://gitlab.com/simonpunk/susfs4ksu) - @simonpunk
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3) - @osm0sis
- [wcedla/android_kernel_oneplus_sm8250_los](https://github.com/wcedla/android_kernel_oneplus_sm8250_los) - 内核源码

## 许可

[GPLv3](LICENSE)
