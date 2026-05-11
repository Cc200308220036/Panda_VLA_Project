# generated from rosidl_generator_py/resource/_idl.py.em
# with input from panda_mujoco_msgs:msg/EEDeltaCommand.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_EEDeltaCommand(type):
    """Metaclass of message 'EEDeltaCommand'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('panda_mujoco_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'panda_mujoco_msgs.msg.EEDeltaCommand')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__ee_delta_command
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__ee_delta_command
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__ee_delta_command
            cls._TYPE_SUPPORT = module.type_support_msg__msg__ee_delta_command
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__ee_delta_command

            from std_msgs.msg import Header
            if Header.__class__._TYPE_SUPPORT is None:
                Header.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class EEDeltaCommand(metaclass=Metaclass_EEDeltaCommand):
    """Message class 'EEDeltaCommand'."""

    __slots__ = [
        '_header',
        '_dx',
        '_dy',
        '_dz',
        '_droll',
        '_dpitch',
        '_dyaw',
        '_gripper',
    ]

    _fields_and_field_types = {
        'header': 'std_msgs/Header',
        'dx': 'double',
        'dy': 'double',
        'dz': 'double',
        'droll': 'double',
        'dpitch': 'double',
        'dyaw': 'double',
        'gripper': 'double',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Header'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from std_msgs.msg import Header
        self.header = kwargs.get('header', Header())
        self.dx = kwargs.get('dx', float())
        self.dy = kwargs.get('dy', float())
        self.dz = kwargs.get('dz', float())
        self.droll = kwargs.get('droll', float())
        self.dpitch = kwargs.get('dpitch', float())
        self.dyaw = kwargs.get('dyaw', float())
        self.gripper = kwargs.get('gripper', float())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.header != other.header:
            return False
        if self.dx != other.dx:
            return False
        if self.dy != other.dy:
            return False
        if self.dz != other.dz:
            return False
        if self.droll != other.droll:
            return False
        if self.dpitch != other.dpitch:
            return False
        if self.dyaw != other.dyaw:
            return False
        if self.gripper != other.gripper:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def header(self):
        """Message field 'header'."""
        return self._header

    @header.setter
    def header(self, value):
        if __debug__:
            from std_msgs.msg import Header
            assert \
                isinstance(value, Header), \
                "The 'header' field must be a sub message of type 'Header'"
        self._header = value

    @builtins.property
    def dx(self):
        """Message field 'dx'."""
        return self._dx

    @dx.setter
    def dx(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'dx' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'dx' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._dx = value

    @builtins.property
    def dy(self):
        """Message field 'dy'."""
        return self._dy

    @dy.setter
    def dy(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'dy' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'dy' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._dy = value

    @builtins.property
    def dz(self):
        """Message field 'dz'."""
        return self._dz

    @dz.setter
    def dz(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'dz' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'dz' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._dz = value

    @builtins.property
    def droll(self):
        """Message field 'droll'."""
        return self._droll

    @droll.setter
    def droll(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'droll' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'droll' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._droll = value

    @builtins.property
    def dpitch(self):
        """Message field 'dpitch'."""
        return self._dpitch

    @dpitch.setter
    def dpitch(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'dpitch' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'dpitch' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._dpitch = value

    @builtins.property
    def dyaw(self):
        """Message field 'dyaw'."""
        return self._dyaw

    @dyaw.setter
    def dyaw(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'dyaw' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'dyaw' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._dyaw = value

    @builtins.property
    def gripper(self):
        """Message field 'gripper'."""
        return self._gripper

    @gripper.setter
    def gripper(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'gripper' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'gripper' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._gripper = value
