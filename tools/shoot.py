"""headless screenshot of the viewer for a model: tools/shoot.py URL OUT.png STEPS.json   (steps = list of JS snippets run after load; 1906x1028 like the app window)"""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(url, out, steps):
    b = cdp.Browser(size=(1906, 1028)); await b.start()
    try:
        await b.goto(url); await b.wait('window.__loaded===true', 90); await asyncio.sleep(0.5)
        for js in steps:
            r = await b.ev(js); await asyncio.sleep(0.9)
            if r is not None: print(r)
        await b.shot(out); print('\n'.join(b.logs[-4:]))
    except Exception:
        print('\n'.join(b.logs[-6:])); raise
    finally: await b.close()
asyncio.run(main(sys.argv[1], sys.argv[2], json.load(open(sys.argv[3])) if len(sys.argv) > 3 else []))
