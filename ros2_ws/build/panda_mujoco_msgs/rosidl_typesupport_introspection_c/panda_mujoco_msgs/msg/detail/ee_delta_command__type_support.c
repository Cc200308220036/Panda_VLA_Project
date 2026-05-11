// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "panda_mujoco_msgs/msg/detail/ee_delta_command__rosidl_typesupport_introspection_c.h"
#include "panda_mujoco_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "panda_mujoco_msgs/msg/detail/ee_delta_command__functions.h"
#include "panda_mujoco_msgs/msg/detail/ee_delta_command__struct.h"


// Include directives for member types
// Member `header`
#include "std_msgs/msg/header.h"
// Member `header`
#include "std_msgs/msg/detail/header__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  panda_mujoco_msgs__msg__EEDeltaCommand__init(message_memory);
}

void panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_fini_function(void * message_memory)
{
  panda_mujoco_msgs__msg__EEDeltaCommand__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_member_array[8] = {
  {
    "header",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(panda_mujoco_msgs__msg__EEDeltaCommand, header),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "dx",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(panda_mujoco_msgs__msg__EEDeltaCommand, dx),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "dy",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(panda_mujoco_msgs__msg__EEDeltaCommand, dy),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "dz",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(panda_mujoco_msgs__msg__EEDeltaCommand, dz),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "droll",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(panda_mujoco_msgs__msg__EEDeltaCommand, droll),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "dpitch",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(panda_mujoco_msgs__msg__EEDeltaCommand, dpitch),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "dyaw",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(panda_mujoco_msgs__msg__EEDeltaCommand, dyaw),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "gripper",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(panda_mujoco_msgs__msg__EEDeltaCommand, gripper),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_members = {
  "panda_mujoco_msgs__msg",  // message namespace
  "EEDeltaCommand",  // message name
  8,  // number of fields
  sizeof(panda_mujoco_msgs__msg__EEDeltaCommand),
  panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_member_array,  // message members
  panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_init_function,  // function to initialize message memory (memory has to be allocated)
  panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_type_support_handle = {
  0,
  &panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_panda_mujoco_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, panda_mujoco_msgs, msg, EEDeltaCommand)() {
  panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, std_msgs, msg, Header)();
  if (!panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_type_support_handle.typesupport_identifier) {
    panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &panda_mujoco_msgs__msg__EEDeltaCommand__rosidl_typesupport_introspection_c__EEDeltaCommand_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
