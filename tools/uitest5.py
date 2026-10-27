"""model picker: library list, switch model via the picker without reloading the page, open a new path"""
import asyncio, sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(port, out):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-ballet'), 'serve', '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1400, 850)); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90)
        first = await b.ev("S.mid"); await b.ev("document.querySelector('#bModels').click()"); await asyncio.sleep(1.5)
        print('rows:', await b.ev("document.querySelectorAll('#picker .covrow').length")); await b.shot(out + '-picker.png')
        await b.ev("[...document.querySelectorAll('#picker .covrow')].find(r=>!r.textContent.includes('(open)')).click()"); await b.wait('window.__loaded===true', 90); await asyncio.sleep(0.5)
        print('switched:', first != await b.ev("S.mid"), '| elements', await b.ev("S.N"))
        print('\n'.join(b.logs[-4:]))
    finally: await b.close(); srv.terminate()
asyncio.run(main(int(sys.argv[1]), sys.argv[2]))
