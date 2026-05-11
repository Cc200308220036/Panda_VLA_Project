// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
// generated code does not contain a copyright notice

#ifndef PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__BUILDER_HPP_
#define PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "panda_mujoco_msgs/msg/detail/ee_delta_command__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace panda_mujoco_msgs
{

namespace msg
{

namespace builder
{

class Init_EEDeltaCommand_gripper
{
public:
  explicit Init_EEDeltaCommand_gripper(::panda_mujoco_msgs::msg::EEDeltaCommand & msg)
  : msg_(msg)
  {}
  ::panda_mujoco_msgs::msg::EEDeltaCommand gripper(::panda_mujoco_msgs::msg::EEDeltaCommand::_gripper_type arg)
  {
    msg_.gripper = std::move(arg);
    return std::move(msg_);
  }

private:
  ::panda_mujoco_msgs::msg::EEDeltaCommand msg_;
};

class Init_EEDeltaCommand_dyaw
{
public:
  explicit Init_EEDeltaCommand_dyaw(::panda_mujoco_msgs::msg::EEDeltaCommand & msg)
  : msg_(msg)
  {}
  Init_EEDeltaCommand_gripper dyaw(::panda_mujoco_msgs::msg::EEDeltaCommand::_dyaw_type arg)
  {
    msg_.dyaw = std::move(arg);
    return Init_EEDeltaCommand_gripper(msg_);
  }

private:
  ::panda_mujoco_msgs::msg::EEDeltaCommand msg_;
};

class Init_EEDeltaCommand_dpitch
{
public:
  explicit Init_EEDeltaCommand_dpitch(::panda_mujoco_msgs::msg::EEDeltaCommand & msg)
  : msg_(msg)
  {}
  Init_EEDeltaCommand_dyaw dpitch(::panda_mujoco_msgs::msg::EEDeltaCommand::_dpitch_type arg)
  {
    msg_.dpitch = std::move(arg);
    return Init_EEDeltaCommand_dyaw(msg_);
  }

private:
  ::panda_mujoco_msgs::msg::EEDeltaCommand msg_;
};

class Init_EEDeltaCommand_droll
{
public:
  explicit Init_EEDeltaCommand_droll(::panda_mujoco_msgs::msg::EEDeltaCommand & msg)
  : msg_(msg)
  {}
  Init_EEDeltaCommand_dpitch droll(::panda_mujoco_msgs::msg::EEDeltaCommand::_droll_type arg)
  {
    msg_.droll = std::move(arg);
    return Init_EEDeltaCommand_dpitch(msg_);
  }

private:
  ::panda_mujoco_msgs::msg::EEDeltaCommand msg_;
};

class Init_EEDeltaCommand_dz
{
public:
  explicit Init_EEDeltaCommand_dz(::panda_mujoco_msgs::msg::EEDeltaCommand & msg)
  : msg_(msg)
  {}
  Init_EEDeltaCommand_droll dz(::panda_mujoco_msgs::msg::EEDeltaCommand::_dz_type arg)
  {
    msg_.dz = std::move(arg);
    return Init_EEDeltaCommand_droll(msg_);
  }

private:
  ::panda_mujoco_msgs::msg::EEDeltaCommand msg_;
};

class Init_EEDeltaCommand_dy
{
public:
  explicit Init_EEDeltaCommand_dy(::panda_mujoco_msgs::msg::EEDeltaCommand & msg)
  : msg_(msg)
  {}
  Init_EEDeltaCommand_dz dy(::panda_mujoco_msgs::msg::EEDeltaCommand::_dy_type arg)
  {
    msg_.dy = std::move(arg);
    return Init_EEDeltaCommand_dz(msg_);
  }

private:
  ::panda_mujoco_msgs::msg::EEDeltaCommand msg_;
};

class Init_EEDeltaCommand_dx
{
public:
  explicit Init_EEDeltaCommand_dx(::panda_mujoco_msgs::msg::EEDeltaCommand & msg)
  : msg_(msg)
  {}
  Init_EEDeltaCommand_dy dx(::panda_mujoco_msgs::msg::EEDeltaCommand::_dx_type arg)
  {
    msg_.dx = std::move(arg);
    return Init_EEDeltaCommand_dy(msg_);
  }

private:
  ::panda_mujoco_msgs::msg::EEDeltaCommand msg_;
};

class Init_EEDeltaCommand_header
{
public:
  Init_EEDeltaCommand_header()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_EEDeltaCommand_dx header(::panda_mujoco_msgs::msg::EEDeltaCommand::_header_type arg)
  {
    msg_.header = std::move(arg);
    return Init_EEDeltaCommand_dx(msg_);
  }

private:
  ::panda_mujoco_msgs::msg::EEDeltaCommand msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::panda_mujoco_msgs::msg::EEDeltaCommand>()
{
  return panda_mujoco_msgs::msg::builder::Init_EEDeltaCommand_header();
}

}  // namespace panda_mujoco_msgs

#endif  // PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__BUILDER_HPP_
