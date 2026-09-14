"""Turn Windows (StandaloneWindows64) asset bundles that were used as fallbacks in the Android bundle folder
into bundles the Android client will load.

Why: the Android UnityCache dump does not contain every bundle, so build_android_bundles.py filled the gaps
with the PC client's bundles. Unity refuses to load a bundle whose serialized files target another platform,
so those assets silently fail on the phone (e.g. K on her motorbike and the dog Pia in the Ancora tutorial).
The prefab/mesh/animation data is platform independent (type trees are present), so flipping the target
platform to Android (13) is enough for them to load. Textures/shaders stay as they are (some may render pink).

The client downloads with UnityWebRequest.GetAssetBundle(url, Hash, crc=0): no CRC check, and Hash is the cache
version key. We therefore give every converted bundle a new Hash in Info.5.2.1.json so phones that already
cached the broken Windows copy download the fixed one.

Usage (from the durango folder):
  python Durango-Server/tools/androidclient/convert_windows_bundles.py --bundles android_bundles --only "models$npc$npc_kbikeprefab" "models$ancora$animals$dog"
  python Durango-Server/tools/androidclient/convert_windows_bundles.py --bundles android_bundles --all
Add --deps to also convert the Windows-platform dependencies of the selected bundles (from Info.5.2.1.json).
Add --dry-run to only report.
"""
import argparse, hashlib, json, os, shutil, sys
import UnityPy
from UnityPy.enums import BuildTarget

ANDROID = 13
WINDOWS = {5, 19}   # StandaloneWindows, StandaloneWindows64


def bundle_platforms(path):
    env = UnityPy.load(path)
    plats = set()
    for f in env.files.values():
        inner = getattr(f, 'files', None) or {}
        for sf in inner.values():
            tp = getattr(sf, 'target_platform', None)
            if tp is not None:
                plats.add(int(tp))
    return env, plats


def base_name(file_name):
    """models$npc$x.prefab.<hash>.bundle -> models$npc$x.prefab.bundle (the manifest Name)"""
    stem = file_name[:-len('.bundle')]
    return stem.rsplit('.', 1)[0] + '.bundle'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bundles', required=True)
    ap.add_argument('--only', nargs='*', default=[], help='bundle name prefixes (without hash)')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--deps', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    info_path = os.path.join(a.bundles, 'Info.5.2.1.json')
    info = json.load(open(info_path, encoding='utf-8'))
    by_name = {e['Name']: e for e in info['FileList']}
    files = {base_name(f): f for f in os.listdir(a.bundles) if f.endswith('.bundle')}

    wanted = set()
    if a.all:
        wanted = set(files)
    for prefix in a.only:
        wanted |= {n for n in files if n.startswith(prefix)}
    if a.deps:
        queue = list(wanted)
        while queue:
            n = queue.pop()
            for d in by_name.get(n, {}).get('Dependencies', []):
                if d in files and d not in wanted:
                    wanted.add(d); queue.append(d)
    if not wanted:
        sys.exit('nothing selected')

    backup = os.path.join(a.bundles, '_windows_originals')
    converted = skipped = failed = 0
    for n in sorted(wanted):
        path = os.path.join(a.bundles, files[n])
        try:
            env, plats = bundle_platforms(path)
        except Exception as e:
            print('  ! cannot read', files[n], e); failed += 1; continue
        if not plats & WINDOWS:
            skipped += 1
            continue
        print(('  would convert ' if a.dry_run else '  convert ') + n, 'platforms', sorted(plats))
        if a.dry_run:
            converted += 1; continue
        try:
            for f in env.files.values():
                for sf in (getattr(f, 'files', None) or {}).values():
                    if getattr(sf, 'target_platform', None) is not None and int(sf.target_platform) in WINDOWS:
                        # UnityPy writes the header from _m_target_platform (target_platform is only the parsed enum),
                        # and only re-serializes a file that is marked changed
                        sf._m_target_platform = ANDROID
                        sf.target_platform = BuildTarget(ANDROID)
                        sf.mark_changed()
            bundle = next(iter(env.files.values()))
            data = bundle.save(packer='lz4')
            os.makedirs(backup, exist_ok=True)
            if not os.path.exists(os.path.join(backup, files[n])):
                shutil.copy2(path, os.path.join(backup, files[n]))
            open(path, 'wb').write(data)
            # verify
            _, after = bundle_platforms(path)
            if after & WINDOWS:
                raise RuntimeError('platform still Windows after save: %s' % sorted(after))
            entry = by_name.get(n)
            if entry is not None:
                entry['Hash'] = hashlib.md5(data).hexdigest()
                entry['Size'] = len(data)
            converted += 1
        except Exception as e:
            print('  ! failed', n, e); failed += 1
            bak = os.path.join(backup, files[n])
            if os.path.exists(bak):
                shutil.copy2(bak, path)
    if not a.dry_run and converted:
        shutil.copy2(info_path, info_path + '.bak')
        json.dump(info, open(info_path, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'converted {converted}, already Android {skipped}, failed {failed}' + (' (dry run)' if a.dry_run else ''))


if __name__ == '__main__':
    main()
