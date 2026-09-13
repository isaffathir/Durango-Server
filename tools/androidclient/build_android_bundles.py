"""Turn a dumped Unity cache (UnityCache/Shared/<name>.<hash>/<cachehash>/__data) into the flat
<name>.<hash>.bundle layout the community server serves with --assetbundles-android."""
import json,os,shutil,sys
cache=r'android_cache/com.nexon.durango.global/files/UnityCache/Shared'
info=r'android_cache/com.nexon.durango.global/files/Info.5.2.1.json'
out=r'android_bundles'; os.makedirs(out,exist_ok=True)
idx=json.load(open(info,encoding='utf-8'))
strip=lambda n: n[:-7] if n.endswith('.bundle') else n
want={strip(f['Name'])+'.'+f['Hash']:f for f in idx['FileList']}
want['preload.'+idx['PreloadHash']]={'Name':'preload.bundle','Hash':idx['PreloadHash'],'Size':None}
have=set(os.listdir(cache))
copied=missing=sizebad=0; missing_list=[]
for key,f in want.items():
    folder=os.path.join(cache,key)
    if not os.path.isdir(folder):
        # try name-only match (different hash)
        alt=[d for d in have if d.rsplit('.',1)[0]==key.rsplit('.',1)[0]]
        if alt: folder=os.path.join(cache,alt[0])
        else: missing+=1; missing_list.append(key); continue
    data=None
    for sub in sorted(os.listdir(folder)):
        p=os.path.join(folder,sub,'__data')
        if os.path.isfile(p): data=p; break
    if not data: missing+=1; missing_list.append(key+' (no __data)'); continue
    dst=os.path.join(out,key+'.bundle')
    if not os.path.exists(dst) or os.path.getsize(dst)!=os.path.getsize(data): shutil.copyfile(data,dst)
    if f.get('Size') and os.path.getsize(data)!=f['Size']: sizebad+=1
    copied+=1
shutil.copyfile(info,os.path.join(out,'Info.5.2.1.json'))
print(f"bundles wanted {len(want)}, copied {copied}, missing {missing}, size mismatches {sizebad}")
print("missing sample:",missing_list[:10])
extra=[d for d in have if d not in want]; print("cache folders not in index:",len(extra),extra[:5])
print("out dir MB:",sum(os.path.getsize(os.path.join(out,x)) for x in os.listdir(out))//1048576)

# ---- fallback: fill bundles missing from the Android cache with the Windows bundle of the same name
win=r'Durango-Server/game/DurangoV2_Data/StreamingAssets/AssetBundles'
winidx=json.load(open(os.path.join(win,'Info.5.2.1.json'),encoding='utf-8'))
winby={strip(f['Name']):f for f in winidx['FileList']}
wdisk={}
for x in os.listdir(win):
    if x.endswith('.bundle'): wdisk.setdefault(x.rsplit('.',2)[0],x)
filled=nofb=0; nofb_list=[]
present=set(x.rsplit('.',2)[0] for x in os.listdir(out) if x.endswith('.bundle'))
for key,f in want.items():
    name=key.rsplit('.',1)[0]
    if name in present: continue
    src=os.path.join(win,wdisk[name]) if name in wdisk else None
    if src and os.path.isfile(src):
        shutil.copyfile(src,os.path.join(out,key+'.bundle')); filled+=1
    else:
        nofb+=1; nofb_list.append(name)
print(f"fallback from Windows set: filled {filled}, still missing {nofb}: {nofb_list[:10]}")
print("out dir MB:",sum(os.path.getsize(os.path.join(out,x)) for x in os.listdir(out))//1048576, "files", len(os.listdir(out)))

# ---- soundbanks: Android-only bank names -> Windows bank of the same name (Wwise banks share event ids)
filled2=0
present=set(x.rsplit('.',2)[0] for x in os.listdir(out) if x.endswith('.bundle'))
for key,f in want.items():
    name=key.rsplit('.',1)[0]
    if name in present or not name.startswith('soundbanks$android$'): continue
    wname=name.replace('soundbanks$android$','soundbanks$windows$',1)
    if wname in wdisk:
        shutil.copyfile(os.path.join(win,wdisk[wname]),os.path.join(out,key+'.bundle')); filled2+=1
print("soundbank fallbacks from windows:",filled2,"| files now",len(os.listdir(out)))
