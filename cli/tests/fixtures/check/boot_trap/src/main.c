/* Traps as soon as it starts: the first-screen run must fail. */
#include "s3w.h"

void s3w_on_start(void)
{
    __builtin_trap();
}
