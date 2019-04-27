# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: teldata.proto

import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from . import monitor_pb2 as monitor__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
    name="teldata.proto",
    package="chec",
    syntax="proto2",
    serialized_options=None,
    serialized_pb=_b(
        '\n\rteldata.proto\x12\x04\x63hec\x1a\rmonitor.proto"?\n\x07TelData\x12\x1b\n\x04time\x18\x01 \x02(\x0b\x32\r.chec.TimeUTC\x12\n\n\x02ra\x18\x02 \x01(\x02\x12\x0b\n\x03\x64\x65\x63\x18\x03 \x01(\x02'
    ),
    dependencies=[monitor__pb2.DESCRIPTOR],
)


_TELDATA = _descriptor.Descriptor(
    name="TelData",
    full_name="chec.TelData",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="time",
            full_name="chec.TelData.time",
            index=0,
            number=1,
            type=11,
            cpp_type=10,
            label=2,
            has_default_value=False,
            default_value=None,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="ra",
            full_name="chec.TelData.ra",
            index=1,
            number=2,
            type=2,
            cpp_type=6,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="dec",
            full_name="chec.TelData.dec",
            index=2,
            number=3,
            type=2,
            cpp_type=6,
            label=1,
            has_default_value=False,
            default_value=float(0),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto2",
    extension_ranges=[],
    oneofs=[],
    serialized_start=38,
    serialized_end=101,
)

_TELDATA.fields_by_name["time"].message_type = monitor__pb2._TIMEUTC
DESCRIPTOR.message_types_by_name["TelData"] = _TELDATA
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

TelData = _reflection.GeneratedProtocolMessageType(
    "TelData",
    (_message.Message,),
    dict(
        DESCRIPTOR=_TELDATA,
        __module__="teldata_pb2"
        # @@protoc_insertion_point(class_scope:chec.TelData)
    ),
)
_sym_db.RegisterMessage(TelData)


# @@protoc_insertion_point(module_scope)
