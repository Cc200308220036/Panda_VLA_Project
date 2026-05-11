// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
// generated code does not contain a copyright notice

#ifndef PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__STRUCT_H_
#define PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.h"

/// Struct defined in msg/EEDeltaCommand in the package panda_mujoco_msgs.
typedef struct panda_mujoco_msgs__msg__EEDeltaCommand
{
  std_msgs__msg__Header header;
  double dx;
  double dy;
  double dz;
  double droll;
  double dpitch;
  double dyaw;
  double gripper;
} panda_mujoco_msgs__msg__EEDeltaCommand;

// Struct for a sequence of panda_mujoco_msgs__msg__EEDeltaCommand.
typedef struct panda_mujoco_msgs__msg__EEDeltaCommand__Sequence
{
  panda_mujoco_msgs__msg__EEDeltaCommand * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} panda_mujoco_msgs__msg__EEDeltaCommand__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__STRUCT_H_
