# PA3ANG WebSDR frequency reader
# Classic WebSDR via Playwright
# Made with Maasbree WebSDR as example / template

import threading
import time
from playwright.sync_api import sync_playwright

class WebSDR:
    def __init__(self,url,frequency_callback=None):
        self.url=url
        self.frequency_callback=frequency_callback
        self.running=False
        self.ready=False
        self.thread=None
        self.page=None
        self.last_frequency=None

    def start(self):
        if self.running:return
        self.running=True
        self.thread=threading.Thread(target=self._worker,daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:return
        self.running=False
        if self.thread:self.thread.join(timeout=3)
        self.thread=None
        self.ready=False
        self.page=None

    def is_ready(self):return self.ready
    def get_frequency(self):return self.last_frequency

    def _worker(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(
                headless=False,
                args=["--window-position=850,50","--window-size=1080,680"]
            )
            context=browser.new_context(viewport={"width":1080,"height":680})
            page=context.new_page()
            self.page=page
            try:
                print(f"Opening WebSDR: {self.url}")
                page.goto(self.url,wait_until="domcontentloaded")
                time.sleep(.1)

                page.evaluate("""() => {
                    const header=document.getElementById('headerwebsdr');
                    if(header)header.style.display='none';
                }""")

                try:
                    audio_started=page.evaluate("""
                        () => {
                            const elements=document.querySelectorAll('input, button');
                            for(const el of elements){
                                const text=(el.value||el.innerText||'').trim().toLowerCase();
                                if(text==='audio start'){
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    if audio_started:
                        print("WebSDR: Audio started")
                    else:
                        print("WebSDR: Audio start button not found")
                except Exception as e:
                    print(f"WebSDR: Audio start error: {e}")

                self.ready=True
                print("WebSDR ready")

                while self.running:
                    self._poll_websdr()
                    time.sleep(0.25)

            except Exception as e:
                print(f"WebSDR error: {e}")

            finally:
                self.ready=False
                self.page=None
                try:browser.close()
                except Exception:pass

    def _poll_websdr(self):
        if not self.page or not self.ready:return
        try:
            frequency=self.page.evaluate("""
                () => {
                    const e=document.forms.freqform.frequency;
                    return e?parseFloat(e.value):null;
                }
            """)

            if frequency is None:return

            frequency_hz=frequency*1000

            if frequency_hz==self.last_frequency:return

            self.last_frequency=frequency_hz
            print(f"WebSDR frequency: {frequency:.2f} kHz")

            if self.frequency_callback:
                self.frequency_callback(frequency_hz)

        except Exception as e:
            print(f"WebSDR read error: {e}")