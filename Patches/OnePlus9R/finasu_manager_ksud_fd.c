// SPDX-License-Identifier: GPL-2.0
// OnePlus 9R / Android 15 / FinaSU v1.6.5 test-only manager bootstrap.
#include <crypto/hash.h>
#include <linux/dcache.h>
#include <linux/file.h>
#include <linux/fs.h>
#include <linux/mm.h>
#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/string.h>

#include "klog.h" // IWYU pragma: keep
#include "manager/manager_identity.h"
#include "supercall/supercall.h"

#define ONEPLUS9R_KSUD_VERIFY_PAYLOAD
#include "oneplus9r_ksud_payload.h"

bool oneplus9r_is_bootstrap_manager(void)
{
    uid_t uid = current_uid().val;

    // Only the statically recognized manager in Android User 0. Do not
    // extend this hand-off to dynamic manager or shared-appid profiles.
    return uid >= 10000 && uid < 20000 && current_euid().val == uid &&
           uid == READ_ONCE(ksu_manager_appid);
}

static bool is_official_library_location(struct file *exe, char *buf, size_t len)
{
    static const char prefix[] = "/data/app/~~";
    static const char package[] = "/me.yuki.fina-";
    static const char suffix[] = "/lib/arm64/libksud.so";
    const char *path, *p;

    path = d_path(&exe->f_path, buf, len);
    if (IS_ERR(path) || strncmp(path, prefix, sizeof(prefix) - 1))
        return false;
    p = strchr(path + sizeof(prefix) - 1, '/');
    if (!p || p == path + sizeof(prefix) - 1 || strncmp(p, package, sizeof(package) - 1))
        return false;
    path = p + sizeof(package) - 1;
    p = strchr(path, '/');
    return p && p != path && !strcmp(p, suffix);
}

static int verify_payload(struct file *exe)
{
    struct crypto_shash *hash;
    struct shash_desc *desc;
    unsigned char digest[sizeof(oneplus9r_ksud_sha256)];
    char *buf;
    loff_t pos = 0;
    int rc = -ENOMEM;

    buf = kmalloc(PAGE_SIZE, GFP_KERNEL);
    if (!buf)
        return -ENOMEM;
    if (!is_official_library_location(exe, buf, PAGE_SIZE)) {
        rc = -EXDEV;
        goto free_buf;
    }

    hash = crypto_alloc_shash("sha256", 0, 0);
    if (IS_ERR(hash)) {
        rc = PTR_ERR(hash);
        goto free_buf;
    }
    desc = kzalloc(sizeof(*desc) + crypto_shash_descsize(hash), GFP_KERNEL);
    if (!desc)
        goto free_hash;
    desc->tfm = hash;
    rc = crypto_shash_init(desc);
    while (!rc && pos < ONEPLUS9R_KSUD_SIZE) {
        size_t count = min_t(loff_t, PAGE_SIZE, ONEPLUS9R_KSUD_SIZE - pos);
        ssize_t n = kernel_read(exe, buf, count, &pos);

        if (n <= 0) {
            rc = n < 0 ? n : -EIO;
            break;
        }
        rc = crypto_shash_update(desc, buf, n);
    }
    if (!rc)
        rc = crypto_shash_final(desc, digest);
    if (!rc && memcmp(digest, oneplus9r_ksud_sha256, sizeof(digest)))
        rc = -EBADMSG;
    kfree(desc);
free_hash:
    crypto_free_shash(hash);
free_buf:
    kfree(buf);
    return rc;
}

void oneplus9r_ksud_after_exec(void)
{
    struct file *exe;
    int rc;

    if (!oneplus9r_is_bootstrap_manager())
        return;
    // Check the executable actually accepted by the kernel, not a mutable
    // userspace filename or argv string. Linux holds the executable against
    // writes while it's mapped as the process image.
    exe = get_task_exe_file(current);
    if (!exe)
        return;
    if (i_size_read(file_inode(exe)) != ONEPLUS9R_KSUD_SIZE)
        goto out;

    rc = verify_payload(exe);
    if (rc == -EXDEV)
        goto out;
    if (rc) {
        pr_warn_ratelimited("fina_9r_ksud_fd: payload_rc=%d pid=%d\n", rc, current->pid);
        goto out;
    }
    if (oneplus9r_is_bootstrap_manager()) {
        // Ordinary CLOEXEC driver FD. All ioctls retain upstream UID and
        // profile checks; do not grant a special su-session capability.
        rc = ksu_install_fd();
        pr_info_ratelimited("fina_9r_ksud_fd: payload_rc=0 fd_rc=%d pid=%d\n",
                            rc < 0 ? rc : 0, current->pid);
    }
out:
    fput(exe);
}
