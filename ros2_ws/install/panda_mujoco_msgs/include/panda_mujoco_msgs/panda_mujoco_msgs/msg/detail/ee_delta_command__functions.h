// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
// generated code does not contain a copyright notice

#ifndef PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__FUNCTIONS_H_
#define PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "panda_mujoco_msgs/msg/rosidl_generator_c__visibility_control.h"

#include "panda_mujoco_msgs/msg/detail/ee_delta_command__struct.h"

/// Initialize msg/EEDeltaCommand message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * panda_mujoco_msgs__msg__EEDeltaCommand
 * )) before or use
 * panda_mujoco_msgs__msg__EEDeltaCommand__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
bool
panda_mujoco_msgs__msg__EEDeltaCommand__init(panda_mujoco_msgs__msg__EEDeltaCommand * msg);

/// Finalize msg/EEDeltaCommand message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
void
panda_mujoco_msgs__msg__EEDeltaCommand__fini(panda_mujoco_msgs__msg__EEDeltaCommand * msg);

/// Create msg/EEDeltaCommand message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * panda_mujoco_msgs__msg__EEDeltaCommand__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
panda_mujoco_msgs__msg__EEDeltaCommand *
panda_mujoco_msgs__msg__EEDeltaCommand__create();

/// Destroy msg/EEDeltaCommand message.
/**
 * It calls
 * panda_mujoco_msgs__msg__EEDeltaCommand__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
void
panda_mujoco_msgs__msg__EEDeltaCommand__destroy(panda_mujoco_msgs__msg__EEDeltaCommand * msg);

/// Check for msg/EEDeltaCommand message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
bool
panda_mujoco_msgs__msg__EEDeltaCommand__are_equal(const panda_mujoco_msgs__msg__EEDeltaCommand * lhs, const panda_mujoco_msgs__msg__EEDeltaCommand * rhs);

/// Copy a msg/EEDeltaCommand message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
bool
panda_mujoco_msgs__msg__EEDeltaCommand__copy(
  const panda_mujoco_msgs__msg__EEDeltaCommand * input,
  panda_mujoco_msgs__msg__EEDeltaCommand * output);

/// Initialize array of msg/EEDeltaCommand messages.
/**
 * It allocates the memory for the number of elements and calls
 * panda_mujoco_msgs__msg__EEDeltaCommand__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
bool
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__init(panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * array, size_t size);

/// Finalize array of msg/EEDeltaCommand messages.
/**
 * It calls
 * panda_mujoco_msgs__msg__EEDeltaCommand__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
void
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__fini(panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * array);

/// Create array of msg/EEDeltaCommand messages.
/**
 * It allocates the memory for the array and calls
 * panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence *
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__create(size_t size);

/// Destroy array of msg/EEDeltaCommand messages.
/**
 * It calls
 * panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
void
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__destroy(panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * array);

/// Check for msg/EEDeltaCommand message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
bool
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__are_equal(const panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * lhs, const panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * rhs);

/// Copy an array of msg/EEDeltaCommand messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_panda_mujoco_msgs
bool
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__copy(
  const panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * input,
  panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__FUNCTIONS_H_
