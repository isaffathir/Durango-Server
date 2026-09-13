"""Rebuild an APK with a replaced global-metadata.dat, then zipalign + sign.

Usage:
  python build_apk.py <in.apk> <patched-metadata.dat> <out.apk> <keystore> <storepass> <alias>
"""
import os, shutil, subprocess, sys, zipfile

BT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build-tools', 'android-15')
META_PATH = 'assets/bin/Data/Managed/Metadata/global-metadata.dat'

def rebuild(src, meta, dst_unsigned, extra=None):
    """extra: {zip entry path: local file path} of additional files to replace."""
    extra = dict(extra or {})
    zin = zipfile.ZipFile(src)
    zout = zipfile.ZipFile(dst_unsigned, 'w')
    replaced = False
    for info in zin.infolist():
        name = info.filename
        if name.startswith('META-INF/') and name.upper().endswith(('.RSA', '.DSA', '.EC', '.SF', 'MANIFEST.MF')):
            continue  # old signature, will be re-signed
        data = zin.read(name)
        if name == META_PATH:
            data = open(meta, 'rb').read(); replaced = True
        elif name in extra:
            data = open(extra.pop(name), 'rb').read(); print('replaced', name)
        ni = zipfile.ZipInfo(name, date_time=info.date_time)
        ni.compress_type = info.compress_type
        ni.external_attr = info.external_attr
        # native libs and resources.arsc must stay STORED for modern Android
        if name.startswith('lib/') or name == 'resources.arsc':
            ni.compress_type = zipfile.ZIP_STORED
        zout.writestr(ni, data)
    zout.close(); zin.close()
    assert replaced, 'metadata entry not found in APK'

def run(cmd):
    print('>', ' '.join(cmd)); subprocess.check_call(cmd, shell=True)

def main(src, meta, dst, ks, pw, alias):
    tmp_unsigned = dst + '.unsigned.apk'; tmp_aligned = dst + '.aligned.apk'
    rebuild(src, meta, tmp_unsigned)
    run([os.path.join(BT, 'zipalign.exe'), '-p', '-f', '4', tmp_unsigned, tmp_aligned])
    run([os.path.join(BT, 'apksigner.bat'), 'sign', '--ks', ks, '--ks-pass', 'pass:' + pw, '--ks-key-alias', alias,
         '--v1-signing-enabled', 'true', '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'true',
         '--out', dst, tmp_aligned])
    run([os.path.join(BT, 'apksigner.bat'), 'verify', '--verbose', dst])
    for t in (tmp_unsigned, tmp_aligned):
        try: os.remove(t)
        except OSError: pass
    print('OK ->', dst, os.path.getsize(dst), 'bytes')

if __name__ == '__main__':
    main(*sys.argv[1:7])
