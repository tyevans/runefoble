#define _GNU_SOURCE
#include <dlfcn.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/inotify.h>

/*
 * Dynamic linker interceptor for inotify_add_watch.
 *
 * Prevents build-time static generators (like Zensical) from crashing with ENOSPC
 * when the developer's workstation has reached fs.inotify.max_user_watches
 * (commonly consumed by IDE file watchers).
 */
int inotify_add_watch(int fd, const char *pathname, uint32_t mask) {
    static int (*orig)(int, const char*, uint32_t) = NULL;
    if (!orig) {
        orig = (int (*)(int, const char*, uint32_t))dlsym(RTLD_NEXT, "inotify_add_watch");
    }
    int res = orig(fd, pathname, mask);
    if (res < 0) {
        return 1000;
    }
    return res;
}
