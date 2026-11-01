#include "model_check.h"
/* Native Windows x64 model: exercise copies surviving Start, activation and
 * actual book routing. Does not execute or emulate extracted ARM firmware.
 */
#define PB_OPDS_CALLBACK_TEST
#include "model_check.h"
#include "opds_open_callback.cpp"

static NativeFunction saved_callback;
static int redraws,opens,start_calls,passthrough;
static void *current_frame=(void *)0x12345678;
static void *expected_finished;
static const char *expected_file="/mnt/ext1/Downloads/book with spaces.fb2.zip";

static void mock_redraw(void *frame) {MODEL_CHECK(frame==current_frame);redraws++;}
static void mock_open(const char *file,const char *position,int flags)
{
    MODEL_CHECK(!strcmp(file,expected_file) && !position && flags==0);
    opens++;
}
void *dlsym(void *scope,const char *name)
{
    MODEL_CHECK(scope==RTLD_DEFAULT);
    if (!strcmp(name,"_ZN10pocketbook10PBAppFrame10m_curFrameE")) return &current_frame;
    if (!strcmp(name,"_ZN10pocketbook10PBAppFrame6ReDrawEv")) return (void *)mock_redraw;
    if (!strcmp(name,"OpenBook")) return (void *)mock_open;
    return NULL;
}
int pb_opds_test_access(const char *file,int mode)
{
    MODEL_CHECK(mode==R_OK);
    if (!strcmp(file,expected_file)) return 0;
    errno=ENOENT;
    return -1;
}
static int mock_start(void *object,void *finished,void *open_book)
{
    MODEL_CHECK(object==(void *)0x5678 && finished==expected_finished);
    NativeFunction *source=(NativeFunction *)open_book;
    MODEL_CHECK(source->manager && source->invoke);
    saved_callback.manager=source->manager;
    saved_callback.invoke=source->invoke;
    source->manager(&saved_callback.storage,&source->storage,2);
    start_calls++;
    return 73;
}
static int invoke_saved(int argc,char **argv)
{
    return saved_callback.invoke(&saved_callback.storage,&argc,&argv);
}
static int custom_invoke(const void *,int *,char ***) {passthrough++;return 19;}

int main(void)
{
    NativeFunction empty={},finished={};
    expected_finished=&finished;
    MODEL_CHECK(pb_opds_start_with_open_callback(mock_start,(void *)0x5678,&finished,&empty)==73);
    MODEL_CHECK(!empty.manager && !finished.manager && start_calls==1);
    /* Multiple native-style copies still work after the temporary was destroyed. */
    NativeFunction next={};
    next.manager=saved_callback.manager;next.invoke=saved_callback.invoke;
    next.manager(&next.storage,&saved_callback.storage,2);
    saved_callback.manager(&saved_callback.storage,&saved_callback.storage,3);
    saved_callback=next;
    const std::type_info *info=NULL;
    saved_callback.manager(&info,&saved_callback.storage,0);
    MODEL_CHECK(info==&typeid(PbOpdsOpenCallbackTag));
    void *functor=NULL;
    saved_callback.manager(&functor,&saved_callback.storage,1);
    MODEL_CHECK(functor==&saved_callback.storage);
    char app[]="explorer.app",blank[]="",bad[]="/unavailable.fb2",option[]="-l";
    char *activation[]={app};
    MODEL_CHECK(invoke_saved(1,activation)==0 && redraws==1 && opens==0);
    char *empty_activation[]={app,blank};
    MODEL_CHECK(invoke_saved(2,empty_activation)==0 && redraws==2);
    char *book[]={app,(char *)expected_file};
    MODEL_CHECK(invoke_saved(2,book)==0 && opens==1);
    char *unsupported[]={app,option};
    MODEL_CHECK(invoke_saved(2,unsupported)==-1 && opens==1);
    char *missing[]={app,bad};
    MODEL_CHECK(invoke_saved(2,missing)==-1 && opens==1);
    MODEL_CHECK(invoke_saved(0,NULL)==-1);
    NativeFunction supplied={};supplied.manager=callback_manager;supplied.invoke=custom_invoke;
    MODEL_CHECK(pb_opds_start_with_open_callback(mock_start,(void *)0x5678,&finished,&supplied)==73);
    MODEL_CHECK(invoke_saved(1,activation)==19 && passthrough==1);
    puts("PASS: callback clone/destroy lifetime and RTTI; activation redraw; native file routing; existing callbacks preserved; invalid requests declined");
    return 0;
}
