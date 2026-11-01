/* Exact U632.6.5.1383 libstdc++ std::function ABI adapter, not a general SDK. */
#ifndef PB_OPDS_OPEN_CALLBACK_H
#define PB_OPDS_OPEN_CALLBACK_H
#ifdef __cplusplus
extern "C" {
#endif
typedef int (*pb_opds_start_fn)(void *,void *,void *);
int pb_opds_start_with_open_callback(pb_opds_start_fn,void *,void *,void *);
#ifdef __cplusplus
}
#endif
#endif
