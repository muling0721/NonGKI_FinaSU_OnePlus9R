#!/usr/bin/env python3
"""4.19 compatibility fixes for FinaSU + SUSFS on the OnePlus 9R kernel.

Run from the kernel source root (the directory that contains drivers/).
All edits are idempotent and fail loudly when an anchor is missing, so a
FinaSU version bump cannot silently produce a broken kernel.
"""

import sys


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def patch_file(path, replacements):
    data = read(path)
    original = data
    for old, new in replacements:
        if new in data:
            continue
        if old not in data:
            raise SystemExit(f"[compat] anchor not found in {path}: {old[:60]!r}")
        data = data.replace(old, new, 1)
    if data != original:
        write(path, data)
        print(f"[compat] patched {path}")
    else:
        print(f"[compat] {path} already patched")


def fs_stat():
    # fs/stat.c uses STATX_SUS_* and susfs_is_current_app_uid() from
    # <linux/susfs_def.h>. SUSFS' inline-hook scripts normally add this
    # include, but this build uses the Tracepoint backend.
    path = "fs/stat.c"
    anchor = "#include <asm/unistd.h>\n"
    block = (
        anchor
        + "\n#ifdef CONFIG_KSU_SUSFS\n"
        + "#include <linux/susfs_def.h>\n"
        + "#endif // #ifdef CONFIG_KSU_SUSFS\n"
    )
    if "linux/susfs_def.h" in read(path):
        print(f"[compat] {path} already patched")
        return
    patch_file(path, [(anchor, block)])


def module_h():
    # FinaSU calls MODULE_IMPORT_NS(), which only exists in 5.4+.
    path = "include/linux/module.h"
    if "define MODULE_IMPORT_NS" in read(path):
        print(f"[compat] {path} already patched")
        return
    anchor = "#endif /* _LINUX_MODULE_H */"
    block = (
        "#ifndef MODULE_IMPORT_NS\n"
        "#define MODULE_IMPORT_NS(ns)\n"
        "#endif\n\n"
        + anchor
    )
    patch_file(path, [(anchor, block)])


def path_umount():
    # FinaSU's kernel_umount uses the 5.9+ path_umount() helper. Provide the
    # same helper on 4.19 using the in-tree do_umount()/may_mount().
    path = "fs/namespace.c"
    data = read(path)
    if "int path_umount(struct path *path, int flags)" in data:
        print(f"[compat] {path} already patched")
        return
    anchor = "int ksys_umount(char __user *name, int flags)"
    block = (
        "#ifdef CONFIG_KSU\n"
        "int path_umount(struct path *path, int flags)\n"
        "{\n"
        "\tstruct mount *mnt;\n"
        "\n"
        "\tif (!path || !path->mnt || !path->dentry)\n"
        "\t\treturn -EINVAL;\n"
        "\n"
        "\tmnt = real_mount(path->mnt);\n"
        "\n"
        "\tif (flags & ~(MNT_FORCE | MNT_DETACH | MNT_EXPIRE | UMOUNT_NOFOLLOW))\n"
        "\t\treturn -EINVAL;\n"
        "\n"
        "\tif (!may_mount())\n"
        "\t\treturn -EPERM;\n"
        "\n"
        "\tif (path->dentry != path->mnt->mnt_root)\n"
        "\t\treturn -EINVAL;\n"
        "\n"
        "\treturn do_umount(mnt, flags);\n"
        "}\n"
        "#endif\n\n"
        + anchor
    )
    patch_file(path, [(anchor, block)])


def finasu_patch_memory():
    path = "FinaSU/kernel/hook/arm64/patch_memory.c"
    replacements = [
        # 4.19 has no p4d level.
        (
            "    pgd_t *pgd;\n    p4d_t *p4d;\n    pud_t *pud;",
            "    pgd_t *pgd;\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 20, 0)\n"
            "    p4d_t *p4d;\n#endif\n    pud_t *pud;",
        ),
        (
            "    p4d = p4d_offset(pgd, addr);\n"
            "    if (p4d_none(*p4d) || p4d_bad(*p4d))\n"
            "        goto fail;\n"
            "#if defined(p4d_leaf)\n"
            "    if (p4d_leaf(*p4d)) {\n"
            "        return __p4d_to_phys(*p4d) + ((addr & ~P4D_MASK));\n"
            "    }\n"
            "#endif\n"
            "\n"
            "    pud = pud_offset(p4d, addr);",
            "#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 20, 0)\n"
            "    p4d = p4d_offset(pgd, addr);\n"
            "    if (p4d_none(*p4d) || p4d_bad(*p4d))\n"
            "        goto fail;\n"
            "#if defined(p4d_leaf)\n"
            "    if (p4d_leaf(*p4d)) {\n"
            "        return __p4d_to_phys(*p4d) + ((addr & ~P4D_MASK));\n"
            "    }\n"
            "#endif\n"
            "\n"
            "    pud = pud_offset(p4d, addr);\n"
            "#else\n"
            "    pud = pud_offset(pgd, addr);\n"
            "#endif",
        ),
        # copy_to_kernel_nofault() was added in 5.8; probe_kernel_write()
        # is the equivalent helper on 4.19.
        (
            "    ret = (int)copy_to_kernel_nofault(map, src, len);",
            "#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 8, 0)\n"
            "    ret = (int)copy_to_kernel_nofault(map, src, len);\n"
            "#else\n"
            "    ret = (int)probe_kernel_write(map, src, len);\n"
            "#endif",
        ),
    ]
    patch_file(path, replacements)


def main():
    if not read("Makefile").startswith("# SPDX"):
        print("[compat] not in a kernel source tree", file=sys.stderr)
        return 1
    fs_stat()
    module_h()
    path_umount()
    finasu_patch_memory()
    return 0


if __name__ == "__main__":
    sys.exit(main())
