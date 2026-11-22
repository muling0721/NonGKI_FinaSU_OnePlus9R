#!/usr/bin/env python3
"""Attach the OnePlus 9R test-only manager ksud handoff to pinned FinaSU."""

import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile

APK_SHA256 = "96acc60da221fba5e8cb906a9e72fc03479eab7603acd005a2f110fedcb19f81"
PAYLOAD_SHA256 = "802d3d0677080747eb7c53f1db29440bf5170efa676f05018a6f47fc015a79ca"


def replace_once(text, old, new, path):
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one occurrence of {old!r}")
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.apk.read_bytes()).hexdigest() != APK_SHA256:
        raise SystemExit("manager APK must exactly match official FinaSU v1.6.5")
    with ZipFile(args.apk) as apk:
        payload = apk.read("lib/arm64-v8a/libksud.so")
    digest = hashlib.sha256(payload)
    if digest.hexdigest() != PAYLOAD_SHA256:
        raise SystemExit("unexpected FinaSU libksud.so digest")

    root = Path("FinaSU/kernel")
    kbuild = root / "Kbuild"
    bridge = root / "hook/syscall_event_bridge.c"
    source = root / "hook/oneplus9r_manager_ksud_fd.c"
    header = root / "include/oneplus9r_ksud_payload.h"
    if source.exists() or header.exists():
        raise SystemExit("manager ksud handoff already applied")
    source_text = args.source.read_text()
    kbuild_text = replace_once(
        kbuild.read_text(), "kernelsu-objs += hook/syscall_event_bridge.o\n",
        "kernelsu-objs += hook/syscall_event_bridge.o\n"
        "kernelsu-objs += hook/oneplus9r_manager_ksud_fd.o\n", kbuild,
    )
    bridge_text = replace_once(
        bridge.read_text(), '#include "preinit/preinit.h"\n',
        '#include "preinit/preinit.h"\n#include "oneplus9r_ksud_payload.h"\n', bridge,
    )
    bridge_text = replace_once(
        bridge_text, "    bool current_is_init = is_init(current_cred());\n",
        "    bool current_is_init = is_init(current_cred());\n"
        "    bool manager_exec = oneplus9r_is_bootstrap_manager();\n", bridge,
    )
    bridge_text = replace_once(
        bridge_text, "        ksu_sulog_emit_pending(pending_root_execve, ret, GFP_KERNEL);\n        return ret;\n    }\n\n"
        "    ret = ksu_syscall_table[orig_nr](regs);\n",
        "        goto out;\n    }\n\n    ret = ksu_syscall_table[orig_nr](regs);\n"
        "out:\n    if (!ret && manager_exec)\n        oneplus9r_ksud_after_exec();\n", bridge,
    )
    header_text = (
        "// Generated from the pinned ARM64 Manager payload.\n"
        "#ifndef ONEPLUS9R_KSUD_PAYLOAD_H\n#define ONEPLUS9R_KSUD_PAYLOAD_H\n\n"
        "bool oneplus9r_is_bootstrap_manager(void);\n"
        "void oneplus9r_ksud_after_exec(void);\n\n"
        "#ifdef ONEPLUS9R_KSUD_VERIFY_PAYLOAD\n"
        f"#define ONEPLUS9R_KSUD_SIZE {len(payload)}LL\n"
        "static const unsigned char oneplus9r_ksud_sha256[] = {\n    "
        + ",\n    ".join(
            ", ".join(f"0x{b:02x}" for b in digest.digest()[i:i + 8])
            for i in range(0, 32, 8)
        )
        + "\n};\n#endif\n#endif\n"
    )
    for path, text in ((source, source_text), (header, header_text),
                       (kbuild, kbuild_text), (bridge, bridge_text)):
        path.write_text(text)
    print(f"Pinned ARM64 Manager libksud.so: size={len(payload)} sha256={digest.hexdigest()}")


if __name__ == "__main__":
    main()
