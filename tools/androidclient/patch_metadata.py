"""Patch string literals inside an IL2CPP global-metadata.dat.

Usage:
  python patch_metadata.py <in.dat> <out.dat> <patches.json>

patches.json: {"old literal exact text": "new text", ...}
Longer replacements are appended to the end of the file and the literal table
entry is re-pointed there (IL2CPP reads literals as dataOffset + index with no
bounds check, so appending is safe). Shorter/equal replacements are written in
place and the length field is shrunk.
"""
import json, struct, sys

def main(src, dst, patches_path):
    d = bytearray(open(src, 'rb').read())
    patches = json.load(open(patches_path, encoding='utf-8'))
    sanity, version = struct.unpack_from('<II', d, 0)
    assert sanity == 0xFAB11BAF, 'not a global-metadata.dat'
    lit_off, lit_cnt, data_off, data_cnt = struct.unpack_from('<iiii', d, 8)
    entries = lit_cnt // 8
    todo = {k.encode('utf-8'): v.encode('utf-8') for k, v in patches.items()}
    done = {}
    append = bytearray()
    for i in range(entries):
        ln, idx = struct.unpack_from('<II', d, lit_off + i * 8)
        s = bytes(d[data_off + idx: data_off + idx + ln])
        if s not in todo:
            continue
        new = todo[s]
        if len(new) <= ln:
            d[data_off + idx: data_off + idx + len(new)] = new
            struct.pack_into('<II', d, lit_off + i * 8, len(new), idx)
            where = 'in place'
        else:
            new_idx = (len(d) + len(append)) - data_off
            append += new
            struct.pack_into('<II', d, lit_off + i * 8, len(new), new_idx)
            where = 'appended'
        done.setdefault(s, []).append((i, where))
    if append:
        d += append
        # keep the header's data size consistent with the new end of data
        struct.pack_into('<i', d, 20, len(d) - data_off)
    open(dst, 'wb').write(d)
    for s, hits in done.items():
        print(f"patched {s.decode()!r} -> {todo[s].decode()!r} at literal(s) {hits}")
    missing = [k.decode() for k in todo if k not in done]
    if missing:
        print("NOT FOUND:", missing)
        sys.exit(2)
    print(f"wrote {dst} ({len(d)} bytes, +{len(append)} appended)")

if __name__ == '__main__':
    main(*sys.argv[1:4])
