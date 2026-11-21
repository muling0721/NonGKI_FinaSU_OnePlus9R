#!/usr/bin/env python3
"""Add read-only FinaSU runtime status to a disposable OnePlus 9R CI tree."""

from pathlib import Path


ROOT = Path("FinaSU/kernel")
HEADER = '#include "oneplus9r_runtime_diag.h"'
STAGES = {
    "INIT": "init_entered",
    "SELINUX": "selinux_init_rc",
    "DISPATCHER": "dispatcher_init_rc",
    "TRACE": "trace_hook_init_rc",
    "REBOOT": "driver_probe_rc",
    "POST_FS": "post_fs_data_seen",
    "WATCH": "packages_watch_rc",
    "PACKAGES": "packages_list_event_seen",
    "LIST": "packages_list_read_rc",
    "SCAN": "manager_scan_seen",
    "SIGNER": "trusted_finasu_signer_seen",
    "MANAGER": "manager_recognized",
}

# Use an out-of-range errno as the marker for a stage that has not been reached.
HEADER_CONTENT = """#ifndef ONEPLUS9R_RUNTIME_DIAG_H
#define ONEPLUS9R_RUNTIME_DIAG_H
#include <linux/atomic.h>

enum oneplus9r_diag_stage {
""" + "".join(f"    DIAG_{key},\n" for key in STAGES) + """    DIAG_COUNT,
};

extern atomic_t oneplus9r_diag[DIAG_COUNT];

static inline void oneplus9r_diag_set(enum oneplus9r_diag_stage stage, int value)
{
    atomic_set(&oneplus9r_diag[stage], value);
}
#endif
"""

PROC_CODE = """#include <linux/proc_fs.h>
#include <linux/seq_file.h>
""" + HEADER + """

atomic_t oneplus9r_diag[DIAG_COUNT] = {
    [0 ... DIAG_COUNT - 1] = ATOMIC_INIT(-4096),
};

static int oneplus9r_diag_show(struct seq_file *m, void *unused)
{
    seq_puts(m, "fina_9r_diag_v2\\nnot_run=-4096\\n");
""" + "".join(
    f'    seq_printf(m, "{name}=%d\\n", atomic_read(&oneplus9r_diag[DIAG_{key}]));\n'
    for key, name in STAGES.items()
) + """    return 0;
}

/* On ROMs where SELinux denies shell access to /proc/fina_9r_diag,
 * dumpstate can still capture these snapshots in its dmesg section. */
static void oneplus9r_diag_log(struct work_struct *work);
static DECLARE_DELAYED_WORK(oneplus9r_diag_work, oneplus9r_diag_log);

static void oneplus9r_diag_log(struct work_struct *work)
{
    static unsigned int sample;

    pr_warn("fina_9r_diag_v2 sample=%u not_run=-4096 "
""" + "".join(f'            "{name}=%d "\n' for name in STAGES.values()) + """            "\\n", ++sample,
""" + ",\n".join(f"            atomic_read(&oneplus9r_diag[DIAG_{key}])" for key in STAGES) + """);
    if (sample < 20)
        schedule_delayed_work(&oneplus9r_diag_work, 30 * HZ);
}
"""

EDITS = {
    "core/init.c": [
        ('#include "preinit/preinit.h"', '#include "preinit/preinit.h"\n' + PROC_CODE.rstrip()),
        ("int __init kernelsu_init(void)\n{\n    int ret;", "int __init kernelsu_init(void)\n{\n    int ret;\n\n"
         "    oneplus9r_diag_set(DIAG_INIT, 1);\n"
         "    schedule_delayed_work(&oneplus9r_diag_work, 30 * HZ);\n"
         '    if (!proc_create_single("fina_9r_diag", 0444, NULL, oneplus9r_diag_show))\n'
         '        pr_warn("could not create OnePlus 9R diagnostic status\\n");'),
        ("void __exit kernelsu_exit(void)\n{", "void __exit kernelsu_exit(void)\n{\n"
         "    cancel_delayed_work_sync(&oneplus9r_diag_work);"),
        ("    ret = ksu_selinux_inode_init();", "    ret = ksu_selinux_inode_init();\n    oneplus9r_diag_set(DIAG_SELINUX, ret);"),
        ("    ret = ksu_syscall_hook_init();", "    ret = ksu_syscall_hook_init();\n    oneplus9r_diag_set(DIAG_DISPATCHER, ret);"),
        ("        ret = ksu_syscall_hook_manager_init();\n        if (!ret)",
         "        ret = ksu_syscall_hook_manager_init();\n        oneplus9r_diag_set(DIAG_TRACE, ret);\n        if (!ret)"),
    ],
    "supercall/supercall.c": [
        ("    rc = register_kprobe(&reboot_kp);", "    rc = register_kprobe(&reboot_kp);\n    oneplus9r_diag_set(DIAG_REBOOT, rc);"),
    ],
    "runtime/boot_event.c": [
        ('    pr_info("on_post_fs_data!\\n");',
         '    pr_info("on_post_fs_data!\\n");\n    oneplus9r_diag_set(DIAG_POST_FS, 1);'),
    ],
    "manager/pkg_observer.c": [
        ('        pr_info("packages.list detected: %d\\n", mask);',
         '        pr_info("packages.list detected: %d\\n", mask);\n        oneplus9r_diag_set(DIAG_PACKAGES, 1);'),
        ("    if (IS_ERR(g))\n        return PTR_ERR(g);\n\n    ret = watch_one_dir(&g_watch);",
         "    if (IS_ERR(g)) {\n        oneplus9r_diag_set(DIAG_WATCH, PTR_ERR(g));\n        return PTR_ERR(g);\n    }\n\n"
         "    ret = watch_one_dir(&g_watch);\n    oneplus9r_diag_set(DIAG_WATCH, ret);"),
    ],
    "manager/throne_tracker.c": [
        ("            ksu_set_manager_appid(np->uid);", "            ksu_set_manager_appid(np->uid);\n            oneplus9r_diag_set(DIAG_MANAGER, 1);"),
        ("                    bool matched = match_apk_signature(candidate_path, &match);",
         "                    bool matched = match_apk_signature(candidate_path, &match);\n"
         '                    if (matched && match.trusted && match.name && !strcmp(match.name, "FinaSU"))\n'
         "                        oneplus9r_diag_set(DIAG_SIGNER, 1);"),
        ('    if (IS_ERR(fp)) {\n        pr_err("%s: open " SYSTEM_PACKAGES_LIST_PATH',
         '    if (IS_ERR(fp)) {\n        oneplus9r_diag_set(DIAG_LIST, PTR_ERR(fp));\n        pr_err("%s: open " SYSTEM_PACKAGES_LIST_PATH'),
        ("    if (!parse_ok) {", "    oneplus9r_diag_set(DIAG_LIST, parse_ok ? 0 : -EINVAL);\n    if (!parse_ok) {"),
        ('        search_manager("/data/app", 2, &uid_list);',
         '        oneplus9r_diag_set(DIAG_SCAN, 1);\n        search_manager("/data/app", 2, &uid_list);'),
    ],
}


def main():
    header = ROOT / "include/oneplus9r_runtime_diag.h"
    changes = {}
    for filename, replacements in EDITS.items():
        path = ROOT / filename
        source = path.read_text()
        if HEADER in source:
            raise SystemExit(f"{path}: runtime diagnostics already applied")
        for old, new in replacements:
            expected = 2 if old.startswith(('        ret = ksu_syscall_hook_manager_init();', '        search_manager(')) else 1
            if source.count(old) != expected:
                raise SystemExit(f"{path}: expected {expected} occurrences of {old!r}")
            source = source.replace(old, new)
        if filename != "core/init.c":
            source = HEADER + "\n" + source
        changes[path] = source
    header.write_text(HEADER_CONTENT)
    for path, source in changes.items():
        path.write_text(source)


if __name__ == "__main__":
    main()
