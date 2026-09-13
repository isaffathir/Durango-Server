import os,re,struct
ip="192.168.1.2"
old=b"http://k1server-clusters.k.nexon.com/live_v2.json"
new=f"http://{ip}:8190/live_v2.json".encode()
pad=len(old)-len(new); assert pad>=0
new=new+b"?"+b"x"*(pad-1) if pad>0 else new
assert len(new)==len(old), (len(new),len(old))
os.makedirs("scene_patched",exist_ok=True)
for f in ["level0","level1","level2.split2"]:
    d=open("apk521_full/assets/bin/Data/"+f,"rb").read()
    n=d.count(old); d2=d.replace(old,new)
    open("scene_patched/"+f,"wb").write(d2); print(f,"replaced",n,"->",new.decode())
