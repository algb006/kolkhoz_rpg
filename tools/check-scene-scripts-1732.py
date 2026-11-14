#!/usr/bin/env python3
"""Run one small isolated Lua fixture; never starts the host or a simulation."""
import csv
import ctypes
import ctypes.util
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
candidates = [ctypes.util.find_library('lua5.4'), '/usr/lib64/liblua-5.4.so']
lib = None
for candidate in candidates:
    if not candidate:
        continue
    try:
        lib = ctypes.CDLL(candidate)
        break
    except OSError:
        continue
if lib is None:
    raise SystemExit('Lua 5.4 shared library unavailable; no runtime validation claimed')
lib.luaL_newstate.restype = ctypes.c_void_p
lib.luaL_openlibs.argtypes = [ctypes.c_void_p]
lib.luaL_loadbufferx.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p]
lib.luaL_loadbufferx.restype = ctypes.c_int
lib.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_longlong, ctypes.c_void_p]
lib.lua_pcallk.restype = ctypes.c_int
lib.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lib.lua_tolstring.restype = ctypes.c_char_p
lib.lua_close.argtypes = [ctypes.c_void_p]

def literal(value):
    return json.dumps(value, ensure_ascii=False)

with sqlite3.connect('file:/home/alex/kolkhoz/db/strings.db?mode=ro', uri=True) as db:
    keys = {key: text for key, text in db.execute('select full_key,source_text from string_source where deprecated=0')}
proposal_paths = [
    ROOT / 'manual/texts/scene-scripts-1732-missing-keys-2026-11-15.csv',
    ROOT / 'manual/texts/zhernova-surplus-line-2026-11-15.csv',
]
for proposals in proposal_paths:
    with proposals.open() as stream:
        for row in csv.DictReader(stream):
            key = row['namespace'] + '.' + row['key']
            if key in keys and keys[key] != row['text_ru']:
                raise SystemExit('Registered key differs from staged authored text: ' + key)
            keys[key] = row['text_ru']

import re
source = ['SCENE_TEST_ROOT=' + literal(str(ROOT)), 'SCENE_TEST_KEYS={}']
for key, text in keys.items():
    if key.startswith(('scene.elder.first_meeting.', 'scene.district.')):
        params = sorted(set(re.findall(r'\{([a-z][a-z0-9_]*)\}', text)))
        source.append('SCENE_TEST_KEYS[' + literal(key) + ']={' + ','.join(map(literal, params)) + '}')
source.append('SCENE_TEST_SCENES={}')
with Path('/home/alex/kolkhoz/host/tables/scenes.csv').open() as stream:
    for row in csv.DictReader(line for line in stream if not line.startswith('#')):
        source.append('SCENE_TEST_SCENES[' + literal(row['key']) + ']=' + literal(row['repeat_policy']))
source.append((ROOT / 'tests/scene_scripts_1732.lua').read_text())
code = '\n'.join(source).encode()
state = lib.luaL_newstate()
if not state:
    raise SystemExit('Could not allocate isolated Lua state')
try:
    lib.luaL_openlibs(state)
    status = lib.luaL_loadbufferx(state, code, len(code), b'1732_review_fixture', b't')
    if not status:
        status = lib.lua_pcallk(state, 0, 0, 0, 0, None)
    if status:
        error = lib.lua_tolstring(state, -1, None)
        raise SystemExit(error.decode() if error else 'Lua fixture failed without diagnostic')
finally:
    lib.lua_close(state)
