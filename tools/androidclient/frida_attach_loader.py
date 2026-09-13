import frida, sys, time, subprocess
dev = frida.get_usb_device(timeout=10)
sess = dev.attach("Durango: Wild Lands")
script = sess.create_script(open("frida_loader.js", encoding="utf-8").read().replace("const FORCE_ONLINE = true;","const FORCE_ONLINE = false;"))
script.on("message", lambda m,d: print(m.get("payload") if m.get("type")=="send" else m, flush=True))
script.load()
t0=time.time()
while time.time()-t0 < float(sys.argv[1] if len(sys.argv)>1 else 60): time.sleep(1)

