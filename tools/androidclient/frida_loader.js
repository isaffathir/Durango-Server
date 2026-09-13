// Trace data-table loading failures in Durango 5.2.1 (arm64).
const RVA = {
  JsonRead1: 0x1b56864, JsonRead2: 0x1b5678c, JsonRead3: 0x1b56518,
  set_Error: 0x18be1a0,          // Yaml.Util.Loader$$set_Error(string)
  set_LoadState: 0x18bdff4,
  get_Error: 0x18be138,
  ABM_Initialize: 0x1580928, ABM_setStatus: 0x1580860,      // Yaml.Util.Loader$$set_LoadState(int)
  LogError1: 0x31207a8,          // UnityEngine.Debug$$LogError(object)
  LogError2: 0x3120884,
  LogException1: 0x3120bb4,
  LogException2: 0x3120c94,
  LogWarning1: 0x311ef64,
  LogWarning2: 0x3120d80,
  set_CurState: 0x175b3cc,
  RequestUrl: 0x175ced0,
};
function s(p) {
  try {
    if (p.isNull()) return '<null>';
    const len = p.add(0x10).readS32();
    if (len < 0 || len > 200000) return '<obj ' + p + '>';
    return p.add(0x14).readUtf16String(Math.min(len, 600));
  } catch (e) { return '<unreadable>'; }
}
function exMessage(p) {  // System.Exception: try common offsets for _message (string)
  for (const off of [0x18, 0x20, 0x28, 0x30]) {
    try { const q = p.add(off).readPointer(); if (!q.isNull()) { const len = q.add(0x10).readS32(); if (len > 0 && len < 2000) return q.add(0x14).readUtf16String(len); } } catch (e) {}
  }
  return '<exception ' + p + '>';
}
function main() {
  const m = Process.findModuleByName('libil2cpp.so'); if (!m) { setTimeout(main, 200); return; }
  const A = n => m.base.add(RVA[n]);
  Interceptor.attach(A('set_Error'), { onEnter(a) {
    console.log('[Loader.Error] a0=' + a[0] + ' a1=' + a[1] + ' s(a0)=' + s(a[0]) + ' s(a1)=' + s(a[1]));
    try { console.log(hexdump(a[0], { length: 96 })); } catch (e) { console.log('hexdump fail ' + e); }
  } });
  const getError = new NativeFunction(A('get_Error'), 'pointer', ['pointer', 'pointer']);
  Interceptor.attach(A('set_LoadState'), { onEnter(a) { const v = a[1].toInt32(); let e = ''; try { e = s(getError(ptr(0), ptr(0))); } catch (x) { e = '<err ' + x + '>'; } console.log('[Loader.State] ' + v + ' Error=' + JSON.stringify(e)); } });
  for (const k of ['LogError1', 'LogError2', 'LogWarning1', 'LogWarning2'])
    Interceptor.attach(A(k), { onEnter(a) { console.log('[' + k + '] ' + s(a[0])); } });
  for (const k of ['LogException1', 'LogException2'])
    Interceptor.attach(A(k), { onEnter(a) { console.log('[' + k + '] ' + exMessage(a[0])); } });
  Interceptor.attach(A('set_CurState'), { onEnter(a) { console.log('[Title.CurState] ' + a[1].toInt32()); } });
  Interceptor.attach(A('RequestUrl'), { onEnter(a) { console.log('[Title.RequestUrl] ' + s(a[1])); } });
  function bytesPreview(p) { try { const n = p.add(0x18).readS32(); if (n < 0 || n > 50000000) return null; return '[' + n + 'B] ' + p.add(0x20).readUtf8String(Math.min(n, 100)).replace(/\s+/g, ' '); } catch (e) { return null; } }
  for (const k of ['JsonRead1', 'JsonRead2', 'JsonRead3'])
    Interceptor.attach(A(k), {
      onEnter(a) { this.tag = k; this.prev = bytesPreview(a[0]) || ('str:' + s(a[0]).slice(0, 100)); },
      onLeave(r) { if (r.isNull()) console.log('[' + this.tag + '] RETURNED NULL for ' + this.prev); }
    });
  Interceptor.attach(A('ABM_Initialize'), { onEnter(a) { console.log('[ABM.Initialize] info=' + s(a[1]) + ' root=' + s(a[2])); } });
  Interceptor.attach(A('ABM_setStatus'), { onEnter(a) { console.log('[ABM.Status] ' + a[1].toInt32() + ' (1 LoadInfo,2 LoadPreload,3 Ready,4 Failed,5 Cached)'); } });
  console.log('[frida] loader hooks installed');
}
main();


