// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__rosidl_typesupport_fastrtps_cpp.hpp.em
// with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
// generated code does not contain a copyright notice

#ifndef PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
#define PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_

#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_interface/macros.h"
#include "panda_mujoco_msgs/msg/rosidl_typesupport_fastrtps_cpp__visibility_control.h"
#include "panda_mujoco_msgs/msg/detail/ee_delta_command__struct.hpp"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

#include "fastcdr/Cdr.h"

namespace panda_mujoco_msgs
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_panda_mujoco_msgs
cdr_serialize(
  const panda_mujoco_msgs::msg::EEDeltaCommand & ros_message,
  eprosima::fastcdr::Cdr & cdr);

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_panda_mujoco_msgs
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  panda_mujoco_msgs::msg::EEDeltaCommand & ros_message);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_panda_mujoco_msgs
get_serialized_size(
  const panda_mujoco_msgs::msg::EEDeltaCommand & ros_message,
  size_t current_alignment);

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_panda_mujoco_msgs
max_serialized_size_EEDeltaCommand(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment);

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace panda_mujoco_msgs

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_panda_mujoco_msgs
const rosidl_message_type_support_t *
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, panda_mujoco_msgs, msg, EEDeltaCommand)();

#ifdef __cplusplus
}
#endif

#endif  // PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__ROSIDL_TYPESUPPORT_FASTRTPS_CPP_HPP_
