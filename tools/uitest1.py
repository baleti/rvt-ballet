import asyncio, sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(model_dir, port, out):
    srv = subprocess.Popen(['~/src/rvt-viewer/rvt-viewer', 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    b = cdp.Browser(); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/' % port)
        await b.wait('window.__loaded===true', 120)
        await asyncio.sleep(1.0); await b.shot(out + '-1.png')
        print('\n'.join(b.logs[-10:]))
    finally:
        await b.close(); srv.terminate()
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
