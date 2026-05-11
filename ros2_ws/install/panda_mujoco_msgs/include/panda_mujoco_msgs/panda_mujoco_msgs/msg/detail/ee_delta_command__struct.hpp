// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
// generated code does not contain a copyright notice

#ifndef PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__STRUCT_HPP_
#define PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__panda_mujoco_msgs__msg__EEDeltaCommand __attribute__((deprecated))
#else
# define DEPRECATED__panda_mujoco_msgs__msg__EEDeltaCommand __declspec(deprecated)
#endif

namespace panda_mujoco_msgs
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct EEDeltaCommand_
{
  using Type = EEDeltaCommand_<ContainerAllocator>;

  explicit EEDeltaCommand_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->dx = 0.0;
      this->dy = 0.0;
      this->dz = 0.0;
      this->droll = 0.0;
      this->dpitch = 0.0;
      this->dyaw = 0.0;
      this->gripper = 0.0;
    }
  }

  explicit EEDeltaCommand_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->dx = 0.0;
      this->dy = 0.0;
      this->dz = 0.0;
      this->droll = 0.0;
      this->dpitch = 0.0;
      this->dyaw = 0.0;
      this->gripper = 0.0;
    }
  }

  // field types and members
  using _header_type =
    std_msgs::msg::Header_<ContainerAllocator>;
  _header_type header;
  using _dx_type =
    double;
  _dx_type dx;
  using _dy_type =
    double;
  _dy_type dy;
  using _dz_type =
    double;
  _dz_type dz;
  using _droll_type =
    double;
  _droll_type droll;
  using _dpitch_type =
    double;
  _dpitch_type dpitch;
  using _dyaw_type =
    double;
  _dyaw_type dyaw;
  using _gripper_type =
    double;
  _gripper_type gripper;

  // setters for named parameter idiom
  Type & set__header(
    const std_msgs::msg::Header_<ContainerAllocator> & _arg)
  {
    this->header = _arg;
    return *this;
  }
  Type & set__dx(
    const double & _arg)
  {
    this->dx = _arg;
    return *this;
  }
  Type & set__dy(
    const double & _arg)
  {
    this->dy = _arg;
    return *this;
  }
  Type & set__dz(
    const double & _arg)
  {
    this->dz = _arg;
    return *this;
  }
  Type & set__droll(
    const double & _arg)
  {
    this->droll = _arg;
    return *this;
  }
  Type & set__dpitch(
    const double & _arg)
  {
    this->dpitch = _arg;
    return *this;
  }
  Type & set__dyaw(
    const double & _arg)
  {
    this->dyaw = _arg;
    return *this;
  }
  Type & set__gripper(
    const double & _arg)
  {
    this->gripper = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator> *;
  using ConstRawPtr =
    const panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__panda_mujoco_msgs__msg__EEDeltaCommand
    std::shared_ptr<panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__panda_mujoco_msgs__msg__EEDeltaCommand
    std::shared_ptr<panda_mujoco_msgs::msg::EEDeltaCommand_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const EEDeltaCommand_ & other) const
  {
    if (this->header != other.header) {
      return false;
    }
    if (this->dx != other.dx) {
      return false;
    }
    if (this->dy != other.dy) {
      return false;
    }
    if (this->dz != other.dz) {
      return false;
    }
    if (this->droll != other.droll) {
      return false;
    }
    if (this->dpitch != other.dpitch) {
      return false;
    }
    if (this->dyaw != other.dyaw) {
      return false;
    }
    if (this->gripper != other.gripper) {
      return false;
    }
    return true;
  }
  bool operator!=(const EEDeltaCommand_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct EEDeltaCommand_

// alias to use template instance with default allocator
using EEDeltaCommand =
  panda_mujoco_msgs::msg::EEDeltaCommand_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace panda_mujoco_msgs

#endif  // PANDA_MUJOCO_MSGS__MSG__DETAIL__EE_DELTA_COMMAND__STRUCT_HPP_
