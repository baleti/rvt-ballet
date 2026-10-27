"""tools/cmdline_test.py URL: drives the rvt-ballet command line with Playwright against a running server (rvt-ballet open FILE --no-browser --port P).
Not part of the pytest run (needs a browser and a converted model). Exits 1 on any failed check."""
import sys, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox', '--disable-gpu', '--use-gl=swiftshader', '--enable-unsafe-swiftshader']); pg = b.new_page(viewport={'width': 1400, 'height': 850}); errs = []; bad = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(sys.argv[1]); pg.wait_for_function("document.querySelector('#status') && /elements/.test(document.querySelector('#status').textContent)", timeout=240000); time.sleep(2)
    def cmd(t): pg.fill('#cmdIn', t); pg.press('#cmdIn', 'Enter'); time.sleep(1.0); return pg.inner_text('#cmdOut')
    def check(name, ok):
        print(('ok   ' if ok else 'FAIL ') + name); ok or bad.append(name)
    check('help', 'SELECT' in cmd('help')); check('select', 'selected' in cmd('select //category !Doors //class *Wall*'))
    n = cmd('sel //category *'); check('select all', 'selected' in n); check('isolate', cmd('i').startswith('isolated')); check('isolate off', cmd('i') == 'isolate off')
    check('hide', cmd('h').startswith('hid')); check('showall', cmd('sa') == 'all shown'); check('bad key', 'unknown key' in cmd('select //zz 1'))
    check('find', 'hits' in cmd('find column')); check('fit', cmd('fit') == 'fit'); check('unknown command', 'unknown command' in cmd('bogus'))
    pg.focus('body'); pg.keyboard.press(':'); check('colon focus', pg.evaluate('document.activeElement.id') == 'cmdIn')
    check('no page errors', not errs); b.close(); sys.exit(1 if bad else 0)
