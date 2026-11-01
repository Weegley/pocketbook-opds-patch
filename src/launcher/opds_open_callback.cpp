/* Fill the missing host callback, rather than intercepting its exception.
 * ABI is verified against native Start, operator= and invocation disassembly.
 * C++ RTTI is compiler-generated and provided by firmware libstdc++, not libc++.
 */
#include "opds_open_callback.h"
#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#ifdef PB_OPDS_RELEASE
#define HOST_LOG(...) ((void)0)
#define HOST_FLUSH() ((void)0)
#else
#define HOST_LOG(...) fprintf(stderr,__VA_ARGS__)
#define HOST_FLUSH() fflush(stderr)
#endif
#ifdef PB_OPDS_CALLBACK_TEST
#include "bridge_test_platform.h"
int pb_opds_test_access(const char *,int);
#define access pb_opds_test_access
#define R_OK 4
#else
#include <dlfcn.h>
#include <unistd.h>
#endif

namespace std { class type_info; }
struct PbOpdsOpenCallbackTag {};

/* Native ARM libstdc++ _Any_data is 8 bytes. The two-pointer layout below also
 * permits a Windows x64 lifecycle model; its 16-byte storage is not ARM code.
 */
union SmallStorage { void *slots[2]; unsigned char bytes[2*sizeof(void *)]; };
struct NativeFunction {
    SmallStorage storage;
    bool (*manager)(void *,const void *,int);
    int (*invoke)(const void *,int *,char ***);
};
#if !defined(PB_OPDS_CALLBACK_TEST)
static_assert(sizeof(void *)==4 && sizeof(NativeFunction)==16,"Wrong target ABI");
static_assert(offsetof(NativeFunction,manager)==8 && offsetof(NativeFunction,invoke)==12,"Wrong function layout");
#endif

/* libstdc++ _Manager_operation: type_info=0, functor_pointer=1, clone=2,
 * destroy=3. The callback is stateless and has no heap allocation; copies stay
 * valid after the temporary passed to Start is destroyed.
 */
static bool callback_manager(void *destination,const void *source,int operation)
{
    switch (operation) {
    case 0: {
        const std::type_info *info=&typeid(PbOpdsOpenCallbackTag);
        memcpy(destination,&info,sizeof(info));
        break;
    }
    case 1: memcpy(destination,&source,sizeof(source)); break;
    case 2: memcpy(destination,source,sizeof(SmallStorage)); break;
    case 3: break;
    default: HOST_LOG("[pb-opds-host] ERROR unknown manager operation=%d\n",operation); break;
    }
    return false;
}

static int activate_opds(void)
{
    /* A payload-free IPC 0x54 is an application activation request. The stock
     * Explorer shows its library; this dedicated host shows its current OPDS
     * frame. No SetActiveTask self-request is generated, avoiding an IPC loop.
     */
    void **frame=(void **)dlsym(RTLD_DEFAULT,"_ZN10pocketbook10PBAppFrame10m_curFrameE");
    void (*redraw)(void *)=(void (*)(void *))dlsym(RTLD_DEFAULT,"_ZN10pocketbook10PBAppFrame6ReDrawEv");
    if (!frame || !*frame || !redraw) {
        HOST_LOG("[pb-opds-host] ERROR activation has no current frame/redraw\n");
        return -1;
    }
    redraw(*frame);
    HOST_LOG("[pb-opds-host] activation handled by current OPDS frame=%p\n",*frame);
    return 0;
}

static int handle_open(int argc,char **argv)
{
    HOST_LOG("[pb-opds-host] openBook argc=%d\n",argc);
    if (argc<1 || !argv || !argv[0]) {
        HOST_LOG("[pb-opds-host] ERROR malformed openBook arguments\n");
        return -1;
    }
    for (int n=0;n<argc;n++) {
        if (!argv[n]) {HOST_LOG("[pb-opds-host] ERROR null argv[%d]\n",n);return -1;}
        HOST_LOG("[pb-opds-host] argv[%d]=%s\n",n,argv[n]);
    }
    if (argc==1 || (argc==2 && !argv[1][0])) return activate_opds();
    /* Both native MainFrame adapters prepend explorer.app. A single absolute
     * file path is handed to the original reader-selection API. Explorer CLI
     * options (-l, -d..., etc.) require Explorer's controller and are explicitly
     * declined here; they are not interpreted as filenames or shell commands.
     */
    if (argc!=2 || argv[1][0]!='/') {
        HOST_LOG("[pb-opds-host] ERROR unsupported Explorer request; no action taken\n");
        return -1;
    }
    if (access(argv[1],R_OK)!=0) {
        HOST_LOG("[pb-opds-host] ERROR unreadable book errno=%d\n",errno);
        return -1;
    }
    void (*open_book)(const char *,const char *,int)=
        (void (*)(const char *,const char *,int))dlsym(RTLD_DEFAULT,"OpenBook");
    if (!open_book) {HOST_LOG("[pb-opds-host] ERROR native OpenBook unavailable\n");return -1;}
    open_book(argv[1],NULL,0);
    HOST_LOG("[pb-opds-host] book passed to native OpenBook\n");
    return 0;
}

static int callback_invoke(const void *,int *argc,char ***argv)
{
    int result=handle_open(*argc,*argv);
    HOST_FLUSH();
    return result;
}

extern "C" int pb_opds_start_with_open_callback(pb_opds_start_fn original,void *object,
                                               void *finished,void *open_book)
{
    NativeFunction *given=(NativeFunction *)open_book;
    if (given->manager) {
        HOST_LOG("[pb-opds-host] preserving supplied openBook callback\n");
        return original(object,finished,open_book);
    }
    NativeFunction callback={};
    callback.manager=callback_manager;
    callback.invoke=callback_invoke;
    HOST_LOG("[pb-opds-host] installing stateless openBook host callback; finished unchanged\n");
    int result=original(object,finished,&callback);
    callback.manager(&callback.storage,&callback.storage,3);
    return result;
}
