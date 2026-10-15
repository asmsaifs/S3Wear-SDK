#include "s3w.h"

void s3w_on_start(void)
{
    s3w_ui_label(s3w_ui_screen(), "tilt", 4);
    s3w_imu_start(50); /* needs the "imu" permission, which the manifest does not list */
}
