"""Independent PLY document I/O for layouts outside the streaming fast path.

Implements the public PLY 1.0 scalar/list format. No external PLY library is
imported. Keep declaration order, custom elements, comments and list types so
georeferencing/export can update coordinates without losing other attributes.
Standard large vertex/triangle files continue to use plyio's bounded fast paths.
"""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import os

import numpy as np

from .plyio import read_header

_TYPE_NAMES = {"i1": "char", "u1": "uchar", "i2": "short", "u2": "ushort",
               "i4": "int", "u4": "uint", "f4": "float", "f8": "double"}


def _type_name(dtype):
    dt = np.dtype(dtype)
    try:
        return _TYPE_NAMES[dt.kind + str(dt.itemsize)]
    except KeyError as exc:
        raise ValueError(f"Unsupported PLY scalar type: {dt}") from exc


def _exact(fh, size):
    data = fh.read(size)
    if len(data) != size:
        raise ValueError("Truncated PLY data")
    return data


def _remaining(fh):
    position = fh.tell()
    fh.seek(0, 2)
    remaining = fh.tell() - position
    fh.seek(position)
    return remaining


def _number(token, dtype):
    dt = np.dtype(dtype)
    if dt.kind in "iu":
        value = int(token)
        bounds = np.iinfo(dt)
        if not bounds.min <= value <= bounds.max:
            raise ValueError("PLY integer outside its declared range")
        return value
    return float(token)


@dataclass
class PlyElement:
    name: str
    data: np.ndarray
    properties: list

    @classmethod
    def describe(cls, data, name):
        array = np.asarray(data)
        if array.ndim != 1 or not array.dtype.names:
            raise ValueError("PLY elements require a 1D structured array")
        props = []
        for field in array.dtype.names:
            dtype = array.dtype.fields[field][0]
            if dtype.subdtype:
                base, shape = dtype.subdtype
                if len(shape) != 1:
                    raise ValueError("PLY lists must be one-dimensional")
                _type_name(base)
                props.append(("list", field, "u1", base.str))
            elif dtype.kind == "O":
                raise ValueError("Declare object-list properties explicitly")
            else:
                _type_name(dtype)
                props.append((field, dtype.str))
        return cls(name, array, props)


class PlyDocument:
    def __init__(self, elements, text=False, comments=(), byte_order="<", obj_info=()):
        self.elements = list(elements)
        self.text = bool(text)
        self.byte_order = byte_order
        self.comments = list(comments)
        self.obj_info = list(obj_info)

    def __getitem__(self, name):
        for element in self.elements:
            if element.name == name:
                return element
        raise KeyError(name)

    @classmethod
    def read(cls, source, mmap=False):
        # mmap intentionally ignored: viewers must never lock project files.
        context = open(source, "rb") if isinstance(source, (str, bytes, os.PathLike)) else nullcontext(source)
        with context as fh:
            header = read_header(fh)
            if header is None:
                raise ValueError("Not a supported PLY document")
            raw, endian, declarations = header
            lines = raw.decode("ascii", "strict").splitlines()
            formats = [line.split() for line in lines if line.startswith("format ")]
            if (lines[0] != "ply" or len(formats) != 1 or len(formats[0]) != 3
                    or formats[0][1] not in ("ascii", "binary_little_endian", "binary_big_endian")
                    or formats[0][2] != "1.0"):
                raise ValueError("Unsupported PLY format/version")
            seen = set()
            elements = []
            for name, count, props in declarations:
                if name in seen or count < 0 or any(p is None for p in props):
                    raise ValueError("Invalid PLY element declaration")
                seen.add(name)
                fields = [p[1] if p[0] == "list" else p[0] for p in props]
                if len(set(fields)) != len(fields) or not fields:
                    raise ValueError("Invalid PLY properties")
                for prop in props:
                    if prop[0] == "list" and np.dtype(prop[2]).kind not in "iu":
                        raise ValueError("PLY list counts must be integers")
                minimum = sum(np.dtype(p[2] if p[0] == "list" else p[1]).itemsize for p in props)
                if count * (minimum if endian else 1) > _remaining(fh):
                    raise ValueError("Truncated PLY element data")
                dtype = np.dtype([(p[1], object) if p[0] == "list" else p for p in props])
                if endian and not any(p[0] == "list" for p in props):
                    data = np.frombuffer(_exact(fh, count * dtype.itemsize), dtype=dtype).copy()
                else:
                    data = np.empty(count, dtype=dtype)
                    for i in range(count):
                        tokens = fh.readline().split() if endian is None else None
                        cursor = 0
                        for prop in props:
                            is_list = prop[0] == "list"
                            field, scalar_type = (prop[1], prop[2]) if is_list else prop
                            scalar_dt = np.dtype(scalar_type)
                            if tokens is not None:
                                if cursor >= len(tokens):
                                    raise ValueError("Missing ASCII PLY property")
                                value = _number(tokens[cursor], scalar_dt)
                                cursor += 1
                            else:
                                value = np.frombuffer(_exact(fh, scalar_dt.itemsize), scalar_dt)[0]
                            if is_list:
                                length = int(value)
                                item_dt = np.dtype(prop[3])
                                if length < 0:
                                    raise ValueError("Negative PLY list length")
                                if tokens is not None:
                                    if length > len(tokens) - cursor:
                                        raise ValueError("Truncated ASCII PLY list")
                                    value = np.array([_number(t, item_dt) for t in tokens[cursor:cursor + length]], dtype=item_dt)
                                    cursor += length
                                else:
                                    if length * item_dt.itemsize > _remaining(fh):
                                        raise ValueError("Truncated binary PLY list")
                                    value = np.frombuffer(_exact(fh, length * item_dt.itemsize), item_dt).copy()
                            data[field][i] = value
                        if tokens is not None and cursor != len(tokens):
                            raise ValueError("Extra ASCII PLY record values")
                elements.append(PlyElement(name, data, props))
            comments = [line[8:] for line in lines if line.startswith("comment ")]
            obj_info = [line[9:] for line in lines if line.startswith("obj_info ")]
            return cls(elements, text=endian is None, byte_order=endian or "<", comments=comments, obj_info=obj_info)

    def write(self, destination):
        if self.byte_order not in ("<", ">"):
            raise ValueError("PLY byte order must be '<' or '>'")
        header = ["ply", "format " + ("ascii" if self.text else
                  "binary_little_endian" if self.byte_order == "<" else "binary_big_endian") + " 1.0"]
        for prefix, values in (("comment ", self.comments), ("obj_info ", self.obj_info)):
            for value in values:
                if "\n" in value or "\r" in value:
                    raise ValueError("PLY header comments must be single-line")
                header.append(prefix + value)
        for element in self.elements:
            header.append(f"element {element.name} {len(element.data)}")
            for prop in element.properties:
                if prop[0] == "list":
                    header.append(f"property list {_type_name(prop[2])} {_type_name(prop[3])} {prop[1]}")
                else:
                    header.append(f"property {_type_name(prop[1])} {prop[0]}")
        header.append("end_header")
        context = open(destination, "wb") if isinstance(destination, (str, bytes, os.PathLike)) else nullcontext(destination)
        with context as fh:
            fh.write(("\n".join(header) + "\n").encode("ascii"))
            for element in self.elements:
                self._write_element(fh, element)

    def _write_element(self, fh, element):
        # Fixed-size vertex/face records are vectorised, including count bytes;
        # saving multi-million-triangle meshes must not loop through Python rows.
        props = element.properties
        if not self.text and all(p[0] != "list" for p in props):
            dtype = np.dtype([(p[0], np.dtype(p[1]).newbyteorder(self.byte_order)) for p in props])
            for start in range(0, len(element.data), 1_000_000):
                block = np.ascontiguousarray(element.data[start:start + 1_000_000].astype(dtype, copy=False))
                fh.write(memoryview(block).cast("B"))
            return
        fixed = all(p[0] != "list" or element.data.dtype.fields[p[1]][0].subdtype for p in props)
        if not self.text and fixed:
            fields = []
            for i, prop in enumerate(props):
                if prop[0] == "list":
                    shape = element.data.dtype.fields[prop[1]][0].subdtype[1]
                    if shape[0] > np.iinfo(np.dtype(prop[2])).max:
                        raise ValueError("PLY list length exceeds its count type")
                    fields.extend([(f"count{i}", np.dtype(prop[2]).newbyteorder(self.byte_order)),
                                   (f"value{i}", np.dtype(prop[3]).newbyteorder(self.byte_order), shape)])
                else:
                    fields.append((f"value{i}", np.dtype(prop[1]).newbyteorder(self.byte_order)))
            for start in range(0, len(element.data), 1_000_000):
                source = element.data[start:start + 1_000_000]
                block = np.empty(len(source), dtype=fields)
                for i, prop in enumerate(props):
                    field = prop[1] if prop[0] == "list" else prop[0]
                    block[f"value{i}"] = source[field]
                    if prop[0] == "list":
                        block[f"count{i}"] = source[field].shape[1]
                fh.write(memoryview(block).cast("B"))
            return
        for row in element.data:
            tokens = []
            for prop in props:
                is_list = prop[0] == "list"
                field, dtype = (prop[1], prop[2]) if is_list else prop
                values = [len(row[field])] if is_list else [row[field]]
                if is_list:
                    if values[0] > np.iinfo(np.dtype(dtype)).max:
                        raise ValueError("PLY list length exceeds its count type")
                    if self.text:
                        tokens.append(str(values[0]))
                    else:
                        fh.write(np.asarray(values, dtype=np.dtype(dtype).newbyteorder(self.byte_order)).tobytes())
                    values, dtype = row[field], prop[3]
                if self.text:
                    dt = np.dtype(dtype)
                    tokens.extend(str(int(v)) if dt.kind in "iu" else format(float(v), ".17g") for v in values)
                else:
                    fh.write(np.asarray(values, dtype=np.dtype(dtype).newbyteorder(self.byte_order)).tobytes())
            if self.text:
                fh.write((" ".join(tokens) + "\n").encode("ascii"))
