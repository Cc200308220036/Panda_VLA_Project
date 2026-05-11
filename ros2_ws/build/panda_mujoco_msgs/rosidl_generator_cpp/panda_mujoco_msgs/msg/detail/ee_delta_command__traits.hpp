// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
// generated code does not contain a copyright notice

#ifndef PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__TRAITS_HPP_
#define PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "panda_mujoco_msgs/msg/detail/ee_delta_command__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__traits.hpp"

namespace panda_mujoco_msgs
{

namespace msg
{

inline void to_flow_style_yaml(
  const EEDeltaCommand & msg,
  std::ostream & out)
{
  out << "{";
  // member: header
  {
    out << "header: ";
    to_flow_style_yaml(msg.header, out);
    out << ", ";
  }

  // member: dx
  {
    out << "dx: ";
    rosidl_generator_traits::value_to_yaml(msg.dx, out);
    out << ", ";
  }

  // member: dy
  {
    out << "dy: ";
    rosidl_generator_traits::value_to_yaml(msg.dy, out);
    out << ", ";
  }

  // member: dz
  {
    out << "dz: ";
    rosidl_generator_traits::value_to_yaml(msg.dz, out);
    out << ", ";
  }

  // member: droll
  {
    out << "droll: ";
    rosidl_generator_traits::value_to_yaml(msg.droll, out);
    out << ", ";
  }

  // member: dpitch
  {
    out << "dpitch: ";
    rosidl_generator_traits::value_to_yaml(msg.dpitch, out);
    out << ", ";
  }

  // member: dyaw
  {
    out << "dyaw: ";
    rosidl_generator_traits::value_to_yaml(msg.dyaw, out);
    out << ", ";
  }

  // member: gripper
  {
    out << "gripper: ";
    rosidl_generator_traits::value_to_yaml(msg.gripper, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const EEDeltaCommand & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: header
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "header:\n";
    to_block_style_yaml(msg.header, out, indentation + 2);
  }

  // member: dx
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "dx: ";
    rosidl_generator_traits::value_to_yaml(msg.dx, out);
    out << "\n";
  }

  // member: dy
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "dy: ";
    rosidl_generator_traits::value_to_yaml(msg.dy, out);
    out << "\n";
  }

  // member: dz
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "dz: ";
    rosidl_generator_traits::value_to_yaml(msg.dz, out);
    out << "\n";
  }

  // member: droll
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "droll: ";
    rosidl_generator_traits::value_to_yaml(msg.droll, out);
    out << "\n";
  }

  // member: dpitch
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "dpitch: ";
    rosidl_generator_traits::value_to_yaml(msg.dpitch, out);
    out << "\n";
  }

  // member: dyaw
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "dyaw: ";
    rosidl_generator_traits::value_to_yaml(msg.dyaw, out);
    out << "\n";
  }

  // member: gripper
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "gripper: ";
    rosidl_generator_traits::value_to_yaml(msg.gripper, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const EEDeltaCommand & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace panda_mujoco_msgs

namespace rosidl_generator_traits
{

[[deprecated("use panda_mujoco_msgs::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const panda_mujoco_msgs::msg::EEDeltaCommand & msg,
  std::ostream & out, size_t indentation = 0)
{
  panda_mujoco_msgs::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use panda_mujoco_msgs::msg::to_yaml() instead")]]
inline std::string to_yaml(const panda_mujoco_msgs::msg::EEDeltaCommand & msg)
{
  return panda_mujoco_msgs::msg::to_yaml(msg);
}

template<>
inline const char * data_type<panda_mujoco_msgs::msg::EEDeltaCommand>()
{
  return "panda_mujoco_msgs::msg::EEDeltaCommand";
}

template<>
inline const char * name<panda_mujoco_msgs::msg::EEDeltaCommand>()
{
  return "panda_mujoco_msgs/msg/EEDeltaCommand";
}

template<>
struct has_fixed_size<panda_mujoco_msgs::msg::EEDeltaCommand>
  : std::integral_constant<bool, has_fixed_size<std_msgs::msg::Header>::value> {};

template<>
struct has_bounded_size<panda_mujoco_msgs::msg::EEDeltaCommand>
  : std::integral_constant<bool, has_bounded_size<std_msgs::msg::Header>::value> {};

template<>
struct is_message<panda_mujoco_msgs::msg::EEDeltaCommand>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__TRAITS_HPP_
