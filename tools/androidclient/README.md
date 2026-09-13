# Android client patch kit (Durango: Wild Lands 5.2.1, arm64)

Turns the genuine `com.nexon.durango.global` 5.2.1 APK into a client for this server:

1. `patch_metadata.py` — rewrites URL literals in `global-metadata.dat` (asset bundle index/root, terrains, maps) to `http://<server-ip>:8190/...`; also `127.0.0.1:` -> `<server-ip>:`.
2. `patch_cluster_online.py` — rewrites the embedded cluster list TextAsset (`assets/bin/Data/b7b0096f71e8a0640be95cc8b863f74d`): our clusters, `offline: false`, same byte length.
3. `patch_scenes.py` — replaces `http://k1server-clusters.k.nexon.com/live_v2.json` in `level0/level1/level2.split2` with our server (same length, padded with a query string).
4. `libil2cpp.so` binary patch (arm64, file offsets == VAs):
   - `0x137b240` `Clusters.get_Offline`: `320003e0` -> `52800000` (return false)
   - `0x137b784` in `Clusters.LoadFromJson`: `bl Dictionary.Clear` -> `d503201f` (NOP). The 5.2.1 build constant-folded `Offline == true`, so the online cluster list was always cleared.
5. `build_apk.py` — rebuilds the APK with replaced files (libs stored uncompressed), zipaligns and signs.
6. `build_android_bundles.py` — flattens a dumped `UnityCache/Shared/<name>.<hash>/<cache>/__data` into `<name>.<hash>.bundle` and fills gaps from the Windows bundle set.

Server side: `data/clusters.json` served at `/live_v2.json`; per-island `AssetBundleUrlBase` must be the server's real address.
Debugging: `frida_loader.js` hooks (RVAs from Il2CppDumper) trace the title state machine, loader and asset-bundle status.
