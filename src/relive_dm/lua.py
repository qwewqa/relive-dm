from __future__ import annotations

import json
import logging
import struct
from io import BytesIO
from pathlib import Path
from typing import TypeAlias

from relive_dm.xxtea import decrypt_xxtea_if_header

logger = logging.getLogger(__name__)

LuaValue: TypeAlias = bool | int | float | str | dict["LuaValue", "LuaValue"] | None


def process_lua(path: Path) -> Path | None:
    out_path = path.with_suffix(".json")
    try:
        value = read_lua_table(path.read_bytes())
        out_path.write_text(json.dumps(value, indent=4, ensure_ascii=False), "utf-8")
        logger.info(f"Converted {path} to {out_path}")
        return out_path
    except (ValueError, NotImplementedError, KeyError):
        logger.warning(f"Failed to convert {path}")
        return None


def read_lua_table(data: bytes) -> LuaValue:
    data = decrypt_xxtea_if_header(data)
    bio = BytesIO(data)
    skip_header(bio)
    return get_prototype(bio).run()


def skip_header(bio: BytesIO):
    magic = bio.read(3)
    if magic != b"\x1bLJ":
        raise ValueError("Invalid magic")
    version = bio.read(1)[0]
    if version != 2:
        raise ValueError("Invalid version")
    flags = get_uleb128(bio)
    if flags not in {0x2, 0xA}:
        raise ValueError("Invalid flags")


def get_prototype(bio: BytesIO) -> Prototype:
    size = get_uleb128(bio)
    flags = bio.read(1)[0]
    argument_count = bio.read(1)[0]
    if argument_count > 0:
        raise NotImplementedError("Arguments are not supported")
    frame_size = bio.read(1)[0]
    up_value_count = bio.read(1)[0]
    if up_value_count > 0:
        raise NotImplementedError("Up values are not supported")
    complex_constant_count = get_uleb128(bio)
    numeric_constant_count = get_uleb128(bio)
    instructions_count = get_uleb128(bio)
    instructions = [
        LuaInstruction(struct.unpack("<I", bio.read(4))[0])
        for _ in range(instructions_count)
    ]
    complex_constants = [
        get_complex_constant(bio) for _ in range(complex_constant_count)
    ]
    numeric_constants = [
        get_numeric_constant(bio) for _ in range(numeric_constant_count)
    ]
    return Prototype(frame_size, instructions, complex_constants, numeric_constants)


class Prototype:
    def __init__(
        self,
        frame_size: int,
        instructions: list[LuaInstruction],
        complex_constants: list[LuaValue],
        numeric_constants: list[int | float],
    ):
        self.frame_size = frame_size
        self.instructions = instructions
        self.complex_constants = complex_constants
        self.numeric_constants = numeric_constants

    def run(self):
        slot: list[LuaValue] = [None] * self.frame_size
        cc = len(self.complex_constants) - 1
        for instr in self.instructions:
            match instr.op:
                case 0x27 | 0x28:
                    slot[instr.a] = self.complex_constants[cc - instr.d]
                case 0x29:
                    slot[instr.a] = struct.unpack("<h", struct.pack("<H", instr.d))[0]
                case 0x2A:
                    slot[instr.a] = self.numeric_constants[instr.d]
                case 0x2B:
                    match instr.d:
                        case 0:
                            slot[instr.a] = None
                        case 1:
                            slot[instr.a] = False
                        case 2:
                            slot[instr.a] = True
                        case _:
                            raise ValueError("Invalid primitive")
                case 0x34:
                    slot[instr.a] = {}
                case 0x35:
                    slot[instr.a] = self.complex_constants[cc - instr.d].copy()
                case 0x3C:
                    slot[instr.b][slot[instr.c]] = slot[instr.a]
                case 0x3D:
                    slot[instr.b][self.complex_constants[cc - instr.c]] = slot[instr.a]
                case 0x3E:
                    slot[instr.b][instr.c] = slot[instr.a]
                case 0x4C:
                    return slot[instr.a]
                case _:
                    raise NotImplementedError(
                        f"Instruction {instr.op} is not supported"
                    )
        raise ValueError("No return statement")


class LuaInstruction:
    def __init__(self, value: int):
        self.value = value

    @property
    def op(self) -> int:
        return self.value & 0xFF

    @property
    def a(self) -> int:
        return (self.value >> 8) & 0xFF

    @property
    def b(self) -> int:
        return (self.value >> 24) & 0xFF

    @property
    def c(self) -> int:
        return (self.value >> 16) & 0xFF

    @property
    def d(self) -> int:
        return (self.value >> 16) & 0xFFFF


def get_complex_constant(bio: BytesIO) -> LuaValue:
    match get_uleb128(bio):
        case 0:
            raise NotImplementedError("Child prototypes are not supported")
        case 1:
            return get_table(bio)
        case 2:
            return get_long(bio)
        case 3:
            return get_ulong(bio)
        case 4:
            raise NotImplementedError("Complex numbers are not supported")
        case n:
            return get_string(bio, n - 5)


def get_table(bio: BytesIO) -> dict[LuaValue, LuaValue]:
    array_count = get_uleb128(bio)
    hash_count = get_uleb128(bio)
    table = {}
    for i in range(array_count):
        next_item = get_table_item(bio)
        if next_item is not None:
            table[i] = next_item
    for i in range(hash_count):
        key = get_table_item(bio)
        value = get_table_item(bio)
        table[key] = value
    return table


def get_table_item(bio: BytesIO) -> LuaValue:
    match get_uleb128(bio):
        case 0:
            return None
        case 1:
            return False
        case 2:
            return True
        case 3:
            return get_int(bio)
        case 4:
            return get_double(bio)
        case n:
            return get_string(bio, n - 5)


def get_numeric_constant(bio: BytesIO) -> int | float:
    part = get_uleb128(bio)
    if (part & 1) == 0:
        return part >> 1
    else:
        bits = get_uleb128(bio) << 32 | part >> 1
        return struct.unpack("<d", struct.pack("<Q", bits))[0]


def get_string(bio: BytesIO, length: int) -> str:
    return bio.read(length).decode("utf-8")


def get_int(bio: BytesIO) -> int:
    return get_uleb128(bio)


def get_double(bio: BytesIO) -> float:
    lo = get_uleb128(bio)
    hi = get_uleb128(bio)
    return struct.unpack("<d", struct.pack("<Q", (hi << 32) | lo))[0]


def get_long(bio: BytesIO) -> int:
    lo = get_uleb128(bio)
    hi = get_uleb128(bio)
    return struct.unpack("<q", struct.pack("<Q", (hi << 32) | lo))[0]


def get_ulong(bio: BytesIO) -> int:
    lo = get_uleb128(bio)
    hi = get_uleb128(bio)
    return (hi << 32) | lo


def get_uleb128(bio: BytesIO) -> int:
    result = 0
    shift = 0
    while True:
        byte = bio.read(1)[0]
        result |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            break
        shift += 7
    return result
