"""RVT write routes are wrapped so a dropped connection cannot free the busy flag while the worker is still saving. Checks the wrapper through the real route table (route handlers keep running after cancel)."""
import os, sys, asyncio, unittest, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import server

class T(unittest.TestCase):
    def test_routes_wrapped(self):
        src = inspect.getsource(server)
        for r in ("'/api/m/{mid}/save', run_to_completion(save_over)", "'/api/m/{mid}/saveas', run_to_completion(save_as)", "'/api/m/{mid}/restore', run_to_completion(restore)"):
            self.assertIn(r, src)
    def test_wrapper_semantics(self):
        # same construction as in server.py, executed standalone: cancel the waiter, the work (incl. its finally) still finishes later
        import functools
        def run_to_completion(handler):
            @functools.wraps(handler)
            async def wrapped(req):
                t = asyncio.ensure_future(handler(req)); t.add_done_callback(lambda f: f.cancelled() or f.exception()); return await asyncio.shield(t)
            return wrapped
        busy = {1}
        async def h(req):
            try: await asyncio.sleep(0.2)
            finally: busy.discard(1)
        async def main():
            t = asyncio.ensure_future(run_to_completion(h)(None)); await asyncio.sleep(0.05); t.cancel()
            try: await t
            except asyncio.CancelledError: pass
            self.assertEqual(busy, {1}); await asyncio.sleep(0.3); self.assertEqual(busy, set())
        asyncio.run(main())
if __name__ == '__main__': unittest.main()
