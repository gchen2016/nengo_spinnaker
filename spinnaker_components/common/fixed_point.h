/* Optimised fixed point methods.
 */

#include <stdint.h>
#include "arm_acle_gcc_selected.h"

#ifndef __FIXED_POINT_H__
#define __FIXED_POINT_H__

typedef int32_t value_t;
#define FP_N_FRAC 15

// Fixed point constants
#define FP_CONST_0_0 0x0
#define FP_CONST_1_0 1 << FP_N_FRAC
#define FP_CONST_2_0 2 << FP_N_FRAC

/*****************************************************************************/
// Convert from an INT64 to appropriate INT32 fixed point representation

static inline int32_t convert_s32_30_s16_15(int64_t value)
{
  return (int32_t) (value >> FP_N_FRAC);
}

/*****************************************************************************/
// Perform a fixed point multiplication
static inline value_t fp_mull(value_t a, value_t b)
{
  int64_t result = __smull(a, b);
  return (value_t) convert_s32_30_s16_15(result);
}

/*****************************************************************************/
// Optimised dot product
// Returns the dot product of two vectors of fixed point values.
// NOTE: This dot product is not saturating at all!

static inline value_t dot_product(uint32_t order, value_t *a, value_t *b)
{
  // Initialise the accumulator with the first product
  register int32_t x = a[0];
  register int32_t y = b[0];
  register int64_t acc = __smull(x, y);

  // Include the remaining product terms (looping backward over the vector)
  for (uint32_t i = order - 1; i > 0; i--)
  {
    // Get the individual components to multiply
    x = a[i];
    y = b[i];

    // Perform a signed multiply with accumulate
    //   acc = acc + x * y;
    acc = __smlal(acc, x, y);
  }

  // Convert from the S32.30 value back to S16.15 before returning
  return (value_t) convert_s32_30_s16_15(acc);
}

/*****************************************************************************/


#endif  // __FIXED_POINT_H__
