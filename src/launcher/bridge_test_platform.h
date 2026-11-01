/* Windows-host mock platform: no ARM execution and no device interaction. */
#include <stdint.h>
#include <setjmp.h>
#define RTLD_NEXT ((void *)(intptr_t)-1)
#define RTLD_DEFAULT ((void *)0)
typedef struct {const char *dli_fname;void *dli_fbase;const char *dli_sname;void *dli_saddr;} Dl_info;
void *dlsym(void *,const char *);
int dladdr(const void *,Dl_info *);
char *dlerror(void);
char *bridge_getenv(const char *);
int bridge_setenv(const char *,const char *,int);
int bridge_unsetenv(const char *);
int bridge_getpid(void);
void bridge_exit(int);
#define getenv bridge_getenv
#define setenv bridge_setenv
#define unsetenv bridge_unsetenv
#define getpid bridge_getpid
#define _exit bridge_exit
