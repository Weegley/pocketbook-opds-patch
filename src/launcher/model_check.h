/* Test checks must execute even when Zig release builds define NDEBUG. */
#ifndef PB_MODEL_CHECK_H
#define PB_MODEL_CHECK_H
#include <stdio.h>
#include <stdlib.h>
#define MODEL_CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr,"MODEL CHECK FAILED: %s at %s:%d\n",#condition,__FILE__,__LINE__); \
        exit(1); \
    } \
} while (0)
#endif
