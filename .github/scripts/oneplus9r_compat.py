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


def task_work_h():
    # task_work_add() takes a plain bool on 4.19; TWA_* came with 5.9.
    path = "include/linux/task_work.h"
    if "define TWA_RESUME" in read(path):
        print(f"[compat] {path} already patched")
        return
    anchor = "#endif\t/* _LINUX_TASK_WORK_H */"
    block = (
        "#ifndef TWA_NONE\n"
        "#define TWA_NONE false\n"
        "#endif\n"
        "#ifndef TWA_RESUME\n"
        "#define TWA_RESUME true\n"
        "#endif\n"
        "#ifndef TWA_SIGNAL\n"
        "#define TWA_SIGNAL true\n"
        "#endif\n\n"
        + anchor
    )
    patch_file(path, [(anchor, block)])


def finasu_seccomp_cache():
    # 4.19's struct seccomp_filter has neither the action cache nor the
    # newer refcount layout. The cache only optimises __NR_reboot passthrough,
    # so turn it into a no-op instead of writing out of bounds.
    path = "FinaSU/kernel/infra/seccomp_cache.c"
    data = read(path)
    if "LINUX_VERSION_CODE < KERNEL_VERSION(5, 9, 0)" in data:
        print(f"[compat] {path} already patched")
        return
    anchor = "struct action_cache {"
    stub = (
        "#if LINUX_VERSION_CODE < KERNEL_VERSION(5, 9, 0)\n"
        "void ksu_seccomp_clear_cache(struct seccomp_filter *filter, int nr)\n"
        "{\n"
        "    (void)filter;\n"
        "    (void)nr;\n"
        "}\n"
        "\n"
        "void ksu_seccomp_allow_cache(struct seccomp_filter *filter, int nr)\n"
        "{\n"
        "    (void)filter;\n"
        "    (void)nr;\n"
        "}\n"
        "#else\n\n"
        + anchor
    )
    if anchor not in data:
        raise SystemExit(f"[compat] anchor not found in {path}")
    data = data.replace(anchor, stub, 1)
    data = data.rstrip("\n") + "\n\n#endif /* LINUX_VERSION_CODE < 5.9.0 */\n"
    write(path, data)
    print(f"[compat] patched {path}")


def path_mount_compat():
    # FinaSU only uses path_mount() to make a mount subtree private
    # (MS_PRIVATE | MS_REC). 4.19 has do_change_type() for that.
    path = "fs/namespace.c"
    data = read(path)
    if "int path_mount(const char *dev_name" in data:
        print(f"[compat] {path} already patched (path_mount)")
        return
    anchor = "int ksys_umount(char __user *name, int flags)"
    block = (
        "#ifdef CONFIG_KSU\n"
        "static int do_change_type(struct path *path, int ms_flags);\n"
        "int path_mount(const char *dev_name, struct path *path,\n"
        "\t       const char *type_page, unsigned long flags, void *data_page)\n"
        "{\n"
        "\tif (flags & (MS_SHARED | MS_PRIVATE | MS_SLAVE | MS_UNBINDABLE))\n"
        "\t\treturn do_change_type(path, flags);\n"
        "\n"
        "\treturn -EINVAL;\n"
        "}\n"
        "#endif\n\n"
        + anchor
    )
    patch_file(path, [(anchor, block)])


def finasu_includes():
    patch_file(
        "FinaSU/kernel/feature/sucompat.c",
        [("#include <linux/pgtable.h>", "#include <asm/pgtable.h>")],
    )
    path = "FinaSU/kernel/manager/apk_sign.c"
    data = read(path)
    if "#include <linux/hex.h>" in data:
        data = data.replace("#include <linux/hex.h>\n", "", 1)
        write(path, data)
        print(f"[compat] patched {path}")
    else:
        print(f"[compat] {path} already patched")
    patch_file(
        "FinaSU/kernel/sulog/event.c",
        [("#include <linux/minmax.h>", "#include <linux/kernel.h>")],
    )

    path = "FinaSU/kernel/infra/su_mount_ns.c"
    data = read(path)
    if "#include <uapi/linux/mount.h>" in data:
        data = data.replace("#include <uapi/linux/mount.h>\n", "", 1)
        write(path, data)
        print(f"[compat] patched {path}")
    else:
        print(f"[compat] {path} already patched")


def uaccess_h():
    # Kernels before 5.8 only provide the probe_*() nofault helpers.
    path = "include/linux/uaccess.h"
    if "define copy_from_kernel_nofault" in read(path):
        print(f"[compat] {path} already patched")
        return
    anchor = "#endif\t\t/* __LINUX_UACCESS_H__ */"
    block = (
        "#ifndef strncpy_from_user_nofault\n"
        "#define strncpy_from_user_nofault(dst, src, count) \\\n"
        "\tstrncpy_from_unsafe_user(dst, src, count)\n"
        "#endif\n"
        "#ifndef copy_from_user_nofault\n"
        "#define copy_from_user_nofault(dst, src, size) probe_user_read(dst, src, size)\n"
        "#endif\n"
        "#ifndef copy_to_user_nofault\n"
        "#define copy_to_user_nofault(dst, src, size) probe_user_write(dst, src, size)\n"
        "#endif\n"
        "#ifndef copy_from_kernel_nofault\n"
        "#define copy_from_kernel_nofault(dst, src, size) probe_kernel_read(dst, src, size)\n"
        "#endif\n\n"
        + anchor
    )
    patch_file(path, [(anchor, block)])


def finasu_selinux():
    # 4.19 exposes struct selinux_policy as struct selinux_ss, keeps the
    # status page/lock inside it, and has no per-state policy mutex.
    kbuild = "FinaSU/kernel/Kbuild"
    data = read(kbuild)
    if "-Dselinux_policy=selinux_ss" not in data:
        anchor = "ccflags-y += -I$(KSU_KERNEL_DIR) -I$(KSU_KERNEL_DIR)/include"
        if anchor not in data:
            raise SystemExit("[compat] Kbuild include anchor not found")
        data = data.replace(anchor, anchor + "\nccflags-y += -Dselinux_policy=selinux_ss", 1)
        write(kbuild, data)
        print(f"[compat] patched {kbuild}")
    else:
        print(f"[compat] {kbuild} already patched")

    header = "FinaSU/kernel/selinux/sepolicy.h"
    data = read(header)
    if "ksu_policy_mutex" not in data:
        data = data.replace(
            "#include <linux/types.h>",
            "#include <linux/types.h>\n#include <linux/mutex.h>",
            1,
        )
        data = data.replace(
            "struct selinux_policy *ksu_dup_sepolicy",
            "extern struct mutex ksu_policy_mutex;\n\nstruct selinux_policy *ksu_dup_sepolicy",
            1,
        )
        write(header, data)
        print(f"[compat] patched {header}")
    else:
        print(f"[compat] {header} already patched")

    sepolicy = "FinaSU/kernel/selinux/sepolicy.c"
    data = read(sepolicy)
    if "DEFINE_MUTEX(ksu_policy_mutex)" not in data:
        anchor = "#define KSU_SUPPORT_ADD_TYPE"
        if anchor not in data:
            raise SystemExit("[compat] sepolicy.c anchor not found")
        data = data.replace(anchor, "DEFINE_MUTEX(ksu_policy_mutex);\n\n" + anchor, 1)
        write(sepolicy, data)
        print(f"[compat] patched {sepolicy}")
    else:
        print(f"[compat] {sepolicy} already patched")

    import re

    for path in ("FinaSU/kernel/feature/selinux_hide.c", "FinaSU/kernel/selinux/rules.c"):
        data = read(path)
        original = data
        data = data.replace("selinux_state.policy_mutex", "ksu_policy_mutex")
        data = data.replace("selinux_state.status_lock", "selinux_state.ss->status_lock")
        data = data.replace("selinux_state.status_page", "selinux_state.ss->status_page")
        data = re.sub(r"selinux_state\.policy\b", "selinux_state.ss", data)
        if data != original:
            write(path, data)
            print(f"[compat] patched {path} (selinux state)")
        else:
            print(f"[compat] {path} already patched")


def finasu_selinux_sidtab():
    # The 5.x sidtab string cache has no counterpart in 4.19.
    path = "FinaSU/kernel/feature/selinux_hide.c"
    data = read(path)
    if "sidtab_sid2str_get" not in data:
        print(f"[compat] {path} already patched (sidtab)")
        return
    start = data.index("static int sidtab_entry_to_string(")
    end = data.index("static void avd_init(struct selinux_policy *policy, struct av_decision *avd)")
    old = data[start:end].rstrip()
    compat = (
        "static int security_sid_to_context_with_policy(struct selinux_policy *policy, u32 sid,\n"
        "                                               char **scontext, u32 *scontext_len)\n"
        "{\n"
        "    struct policydb *policydb = &policy->policydb;\n"
        "    struct context *context;\n"
        "    int rc;\n"
        "\n"
        "    if (scontext)\n"
        "        *scontext = NULL;\n"
        "    *scontext_len = 0;\n"
        "\n"
        "    context = sidtab_search(policy->sidtab, sid);\n"
        "    if (!context) {\n"
        "        pr_err(\"SELinux: %s: unrecognized SID %d\\n\", __func__, sid);\n"
        "        return -EINVAL;\n"
        "    }\n"
        "\n"
        "    rc = context_struct_to_string(policydb, context, scontext, scontext_len);\n"
        "    return rc;\n"
        "}"
    )
    new = (
        "#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 0, 0)\n"
        + old
        + "\n#else\n"
        + compat
        + "\n#endif\n\n"
    )
    data = data[:start] + new + data[end:]
    write(path, data)
    print(f"[compat] patched {path} (sidtab)")


def main():
    if not read("Makefile").startswith("# SPDX"):
        print("[compat] not in a kernel source tree", file=sys.stderr)
        return 1
    fs_stat()
    module_h()
    uaccess_h()
    path_umount()
    path_mount_compat()
    finasu_includes()
    finasu_selinux()
    finasu_selinux_sidtab()
    task_work_h()
    finasu_seccomp_cache()
    finasu_patch_memory()
    return 0


if __name__ == "__main__":
    sys.exit(main())
