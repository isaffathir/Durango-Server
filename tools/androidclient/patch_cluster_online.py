"""Rewrite the embedded cluster list TextAsset: point clusters at our servers and set offline=false,
keeping the serialized byte length identical."""
import json, struct, sys
src, dst, ip = sys.argv[1], sys.argv[2], sys.argv[3]
d = bytearray(open(src, 'rb').read())
i = d.find(b'{\n  "clusters"'); assert i != -1
ln = struct.unpack_from('<i', d, i - 4)[0]
obj = json.loads(bytes(d[i:i + ln]).decode('utf-8'))
obj['clusters'] = {
    'ancora':   {'gateway_url_root': f'http://{ip}:8190', 'name': {'en_US': 'Ancora (Starter)', 'id_ID': 'Ancora (Pemula)'}},
    'personal': {'gateway_url_root': f'http://{ip}:8290', 'name': {'en_US': 'Personal Island', 'id_ID': 'Pulau Pribadi'}},
}
obj['offline'] = False
compact = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
assert len(compact) <= ln, (len(compact), ln)
padded = compact[:-1] + b' ' * (ln - len(compact)) + b'}'
d[i:i + ln] = padded
open(dst, 'wb').write(d)
print('cluster asset written: offline=false,', len(padded), 'bytes ==', ln)
print(json.dumps(obj, ensure_ascii=False))
