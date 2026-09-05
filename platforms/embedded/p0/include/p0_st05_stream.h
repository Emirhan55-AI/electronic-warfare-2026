#ifndef P0_ST05_STREAM_H
#define P0_ST05_STREAM_H

#include <stddef.h>

#include "p0_st05_wideband.h"

P0_API size_t p0_st05_stream_state_bytes(void);

P0_API int p0_st05_stream_init(void *memory, size_t memory_bytes);

P0_API int p0_st05_stream_reset(void *memory, size_t memory_bytes);

/* Checkpoint covers exactly one update; reset requires a full state copy. */
P0_API size_t p0_st05_stream_checkpoint_bytes(void);
P0_API int p0_st05_stream_checkpoint_save(
    const void *memory, size_t memory_bytes, void *checkpoint, size_t checkpoint_bytes);
P0_API int p0_st05_stream_checkpoint_restore(
    void *memory, size_t memory_bytes, const void *checkpoint, size_t checkpoint_bytes);

P0_API int p0_st05_stream_update(
    void *memory,
    size_t memory_bytes,
    const double *power,
    size_t power_count,
    p0_st05_result_t *result,
    int *result_valid
);

#endif
