// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
// generated code does not contain a copyright notice
#include "panda_mujoco_msgs/msg/detail/ee_delta_command__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `header`
#include "std_msgs/msg/detail/header__functions.h"

bool
panda_mujoco_msgs__msg__EEDeltaCommand__init(panda_mujoco_msgs__msg__EEDeltaCommand * msg)
{
  if (!msg) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__init(&msg->header)) {
    panda_mujoco_msgs__msg__EEDeltaCommand__fini(msg);
    return false;
  }
  // dx
  // dy
  // dz
  // droll
  // dpitch
  // dyaw
  // gripper
  return true;
}

void
panda_mujoco_msgs__msg__EEDeltaCommand__fini(panda_mujoco_msgs__msg__EEDeltaCommand * msg)
{
  if (!msg) {
    return;
  }
  // header
  std_msgs__msg__Header__fini(&msg->header);
  // dx
  // dy
  // dz
  // droll
  // dpitch
  // dyaw
  // gripper
}

bool
panda_mujoco_msgs__msg__EEDeltaCommand__are_equal(const panda_mujoco_msgs__msg__EEDeltaCommand * lhs, const panda_mujoco_msgs__msg__EEDeltaCommand * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__are_equal(
      &(lhs->header), &(rhs->header)))
  {
    return false;
  }
  // dx
  if (lhs->dx != rhs->dx) {
    return false;
  }
  // dy
  if (lhs->dy != rhs->dy) {
    return false;
  }
  // dz
  if (lhs->dz != rhs->dz) {
    return false;
  }
  // droll
  if (lhs->droll != rhs->droll) {
    return false;
  }
  // dpitch
  if (lhs->dpitch != rhs->dpitch) {
    return false;
  }
  // dyaw
  if (lhs->dyaw != rhs->dyaw) {
    return false;
  }
  // gripper
  if (lhs->gripper != rhs->gripper) {
    return false;
  }
  return true;
}

bool
panda_mujoco_msgs__msg__EEDeltaCommand__copy(
  const panda_mujoco_msgs__msg__EEDeltaCommand * input,
  panda_mujoco_msgs__msg__EEDeltaCommand * output)
{
  if (!input || !output) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__copy(
      &(input->header), &(output->header)))
  {
    return false;
  }
  // dx
  output->dx = input->dx;
  // dy
  output->dy = input->dy;
  // dz
  output->dz = input->dz;
  // droll
  output->droll = input->droll;
  // dpitch
  output->dpitch = input->dpitch;
  // dyaw
  output->dyaw = input->dyaw;
  // gripper
  output->gripper = input->gripper;
  return true;
}

panda_mujoco_msgs__msg__EEDeltaCommand *
panda_mujoco_msgs__msg__EEDeltaCommand__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  panda_mujoco_msgs__msg__EEDeltaCommand * msg = (panda_mujoco_msgs__msg__EEDeltaCommand *)allocator.allocate(sizeof(panda_mujoco_msgs__msg__EEDeltaCommand), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(panda_mujoco_msgs__msg__EEDeltaCommand));
  bool success = panda_mujoco_msgs__msg__EEDeltaCommand__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
panda_mujoco_msgs__msg__EEDeltaCommand__destroy(panda_mujoco_msgs__msg__EEDeltaCommand * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    panda_mujoco_msgs__msg__EEDeltaCommand__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__init(panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  panda_mujoco_msgs__msg__EEDeltaCommand * data = NULL;

  if (size) {
    data = (panda_mujoco_msgs__msg__EEDeltaCommand *)allocator.zero_allocate(size, sizeof(panda_mujoco_msgs__msg__EEDeltaCommand), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = panda_mujoco_msgs__msg__EEDeltaCommand__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        panda_mujoco_msgs__msg__EEDeltaCommand__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__fini(panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      panda_mujoco_msgs__msg__EEDeltaCommand__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

panda_mujoco_msgs__msg__EEDeltaCommand__Sequence *
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * array = (panda_mujoco_msgs__msg__EEDeltaCommand__Sequence *)allocator.allocate(sizeof(panda_mujoco_msgs__msg__EEDeltaCommand__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__destroy(panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__are_equal(const panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * lhs, const panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!panda_mujoco_msgs__msg__EEDeltaCommand__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
panda_mujoco_msgs__msg__EEDeltaCommand__Sequence__copy(
  const panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * input,
  panda_mujoco_msgs__msg__EEDeltaCommand__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(panda_mujoco_msgs__msg__EEDeltaCommand);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    panda_mujoco_msgs__msg__EEDeltaCommand * data =
      (panda_mujoco_msgs__msg__EEDeltaCommand *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!panda_mujoco_msgs__msg__EEDeltaCommand__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          panda_mujoco_msgs__msg__EEDeltaCommand__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!panda_mujoco_msgs__msg__EEDeltaCommand__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
