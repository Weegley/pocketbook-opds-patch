/* PB632 U632.6.5.1383: production host, no tracing or network interposition.
 * Preserves the tested bootstrap/event order and supplies the missing callback.
 */
#define _GNU_SOURCE
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#ifdef PB_OPDS_BRIDGE_TEST
#include "bridge_test_platform.h"
#else
#include <dlfcn.h>
#include <unistd.h>
#endif
#include "opds_open_callback.h"

typedef int (*iv_handler)(int,int,int);
typedef void (*inkview_main_fn)(iv_handler);
typedef iv_handler (*set_handler_fn)(iv_handler);
typedef void (*timer_fn)(const char *,void (*)(void),int);
enum { EVT_INIT=21, EVT_SHOW=23, EVT_POINTERUP=30 };
static const char FRAME_SYMBOL[]="_ZN10pocketbook10PBAppFrame12main_handlerEiii";
static const char START_SYMBOL[]="_ZN10pocketbook4opds7OpdsApp5StartESt8functionIFviEES2_IFiiPPcEE";
static iv_handler original_handler,framework_handler;
static set_handler_fn install_handler;
static timer_fn weak_timer;
static int scheduled,started;

static void restore_child_environment(void)
{
    const char *saved=getenv("PB_OPDS_SAVED_PRELOAD");
    if(saved && *saved)setenv("LD_PRELOAD",saved,1);else unsetenv("LD_PRELOAD");
    saved=getenv("PB_OPDS_SAVED_LIBRARY_PATH");
    if(saved && *saved)setenv("LD_LIBRARY_PATH",saved,1);else unsetenv("LD_LIBRARY_PATH");
    unsetenv("PB_OPDS_SAVED_PRELOAD");
    unsetenv("PB_OPDS_SAVED_LIBRARY_PATH");
}

static void start_opds(void)
{
    if(started)return;
    started=1;
    original_handler(EVT_POINTERUP,0,0);
    install_handler(framework_handler);
}

static int bootstrap_handler(int event,int p1,int p2)
{
    if(started)return 0;
    if(event==EVT_POINTERUP){start_opds();return 0;}
    int result=original_handler(event,p1,p2);
    if(event==EVT_SHOW && !scheduled){
        scheduled=1;
        weak_timer("PB632OpdsDispatchBootstrap",start_opds,100);
    }
    return result;
}

__attribute__((visibility("default"))) void InkViewMain(iv_handler handler)
{
    inkview_main_fn real_main=(inkview_main_fn)dlsym(RTLD_NEXT,"InkViewMain");
    if(started && real_main){real_main(handler);return;}
    original_handler=handler;
    framework_handler=(iv_handler)dlsym(RTLD_DEFAULT,FRAME_SYMBOL);
    install_handler=(set_handler_fn)dlsym(RTLD_DEFAULT,"SetEventHandler");
    weak_timer=(timer_fn)dlsym(RTLD_DEFAULT,"SetWeakTimer");
    restore_child_environment();
    if(!real_main || !handler || !framework_handler || !install_handler || !weak_timer)_exit(127);
    real_main(bootstrap_handler);
}

__attribute__((visibility("default")))
int release_start(void *,void *,void *) __asm__("_ZN10pocketbook4opds7OpdsApp5StartESt8functionIFviEES2_IFiiPPcEE");
int release_start(void *object,void *finished,void *open_book)
{
    int saved_errno=errno;
    pb_opds_start_fn original=(pb_opds_start_fn)dlsym(RTLD_NEXT,START_SYMBOL);
    if(!original)_exit(127);
    errno=saved_errno;
    return pb_opds_start_with_open_callback(original,object,finished,open_book);
}
