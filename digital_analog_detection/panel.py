"""
panel.py
--------
RF Modulasyon Paneli.

Kullanim:
  1) Once GRC'deki RX flowgraph'ini (hackrf_inspector.grc) calistir -> ZMQ PUB
     akisi tcp://127.0.0.1:5555 uzerinden yayinlaniyor olmali (senin zaten
     dogruladigin kurulum).
  2) Bu dosyayi C:\\DAT\\scripts\\ klasorune, feature_extractor_v1.py,
     gen_signal.py ve classifier_model.py ile AYNI klasore koy.
  3) CMD'den calistir:
         cd /d C:\\DAT\\scripts
         python panel.py
  4) Panelde "AM" / "FM" / "BPSK" / "QPSK" yaz, "Gonder (Start TX)" bas.
     Alttaki "RX Canli Istatistikler" ve "KARAR" alani, SENIN GIRDIGIN
     ETIKETI GORMEDEN, sadece havadan aldigi IQ'dan hesaplaniyor.

ONEMLI - TEK KONTROL ETMEN GEREKEN NOKTA:
  Asagida _call_wideband_detect() fonksiyonunda feature_extractor_v1.py
  icindeki wideband_detect()'in tam donus sirasini (is_signal, margin_db,
  cfo_hz, ...) varsayiyorum: (is_signal: bool, margin_db: float, cfo_hz: float).
  Eger senin fonksiyonun farkli sirada donuyorsa (mesela once margin sonra
  is_signal), SADECE o fonksiyonun icindeki tek satiri kendi sirana gore
  degistirmen yeterli - kodda '<<< BURAYI KONTROL ET' ile isaretledim.
"""

import os
import sys
import time
import threading
import queue
import subprocess

import numpy as np
import zmq
import tkinter as tk
from tkinter import ttk, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from feature_extractor_v1 import (   # noqa: E402  (senin dogrulanmis dosyan)
    wideband_detect,
    channelize,
    normalize_iq,
    extract_features,
    RX_SAMPLE_RATE,
    BLOCK_SAMPLES,
    ZMQ_ADDR,
)

import gen_signal          # noqa: E402  (bu paketle birlikte geldi)
import classifier_model    # noqa: E402  (bu paketle birlikte geldi)

TX_SERIAL = "a32868dc35138247"
HACKRF_TRANSFER_CMD = "hackrf_transfer"   # PATH'te olmali (radioconda ortami)
IQ_OUT_FILE = os.path.join(SCRIPT_DIR, "panel_tx_out.iq")
VALID_MODS = ["AM", "FM", "BPSK", "QPSK"]


def _call_wideband_detect(block):
    """
    feature_extractor_v1.wideband_detect() ciktisini (is_signal, margin_db,
    cfo_hz) formatina normalize eder.

    <<< BURAYI KONTROL ET: senin wideband_detect() fonksiyonun farkli sirada
    donuyorsa (ornegin (margin_db, cfo_hz, is_signal) gibi), asagidaki
    unpacking satirini kendi sirana gore degistir.
    """
    result = wideband_detect(block)
    is_signal, margin_db, cfo_hz = result[0], result[1], result[2]
    return bool(is_signal), float(margin_db), float(cfo_hz)


class TXController:
    """
    MIMARI NOTU (onemli): hackrf_transfer'i -R (sonsuz tekrar) ile TEK bir
    surekli surec olarak baslatip sonra onu bir sinyalle (CTRL+BREAK/CTRL+C)
    "nazikce" durdurmaya calismak bu Windows/radioconda derlemesinde
    GUVENILIR CALISMIYOR -- surec sinyali yakalamiyor, hep zorla kapatmaya
    (taskkill /F) dusuyoruz, bu da cihaza duzgun "TX'i durdur" komutunun
    hic gitmemesine ve havada sinyal kalmasina yol aciyordu.

    Bunun yerine: -R KULLANMIYORUZ. Dosya zaten kisa (gen_signal.DURATION_SEC
    ~2 saniye). hackrf_transfer'i TEK GECIS icin baslatiyoruz; dosya
    bitince surec KENDI KENDINE, DOGAL yoldan kapanir (hackrf_close() bu
    normal/rutin cikis yolunda calisir, sinyal yakalamaya hic gerek yok).
    "Surekli yayin" hissi, Python'un ust uste yeni bir kisa gecis
    baslatmasindan gelir. "Durdur" basildiginda sadece "bir sonrakini
    baslatma" bayragini set ediyoruz -- o an devam eden gecis zaten en
    fazla ~2 saniye icinde kendiliginden, DUZGUN sekilde bitecek.
    """

    def __init__(self):
        self.proc = None
        self.lock = threading.Lock()
        self._should_run = threading.Event()
        self._loop_thread = None

    def _kill_all_hackrf_transfer_system_wide(self):
        # Onceki (artik kullanilmayan) -R mimarisinden kalma zombi surecleri
        # temizlemek icin hala faydali bir guvenlik onlemi.
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "hackrf_transfer.exe"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception:
                pass
            time.sleep(0.3)

    def _build_cmd(self, mod):
        freq_hz, tx_gain = gen_signal.generate(mod, IQ_OUT_FILE)
        cmd = [
            HACKRF_TRANSFER_CMD,
            "-d", TX_SERIAL,
            "-t", IQ_OUT_FILE,
            "-f", str(int(freq_hz)),
            "-s", str(int(RX_SAMPLE_RATE)),
            "-x", str(tx_gain),
            "-a", "1",
            # -R YOK: tek gecis, dosya bitince surec kendiliginden kapanir.
        ]
        return cmd, freq_hz, tx_gain

    def _launch(self, cmd):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        return subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            creationflags=creationflags,
        )

    def start(self, mod, status_cb):
        self.stop()
        self._kill_all_hackrf_transfer_system_wide()

        cmd, freq_hz, tx_gain = self._build_cmd(mod)
        status_cb(f"TX baslatiliyor: {mod}  freq={freq_hz/1e6:.4f} MHz  gain={tx_gain}")
        proc = self._launch(cmd)
        with self.lock:
            self.proc = proc

        # hackrf_transfer cihazi acamazsa (mesela hala mesgulse) genelde
        # <1 saniye icinde hemen cikar. Bunu yakalayip kullaniciya GERCEK
        # hatayi gostermek icin kisa bir sure bekleyip kontrol ediyoruz --
        # aksi halde panel "TX AKTIF" derken aslinda hicbir sey gonderilmiyor
        # olabilirdi (daha once yasanan sorunun tam kaynagi buydu).
        time.sleep(0.8)
        if proc.poll() is not None:
            exit_code = proc.returncode
            try:
                err = proc.stderr.read().decode(errors="replace").strip()
            except Exception:
                err = ""
            with self.lock:
                self.proc = None
            raise RuntimeError(
                f"hackrf_transfer baslatilamadi / hemen kapandi (exit={exit_code}).\n"
                f"Muhtemel sebep: cihaz baska bir surec tarafindan kilitli, "
                f"ya da HackRF bagli degil.\n\nhackrf_transfer ciktisi:\n{err or '(bos)'}"
            )

        # Ilk gecis basariyla basladi. Simdi arka plandaki dongu thread'i
        # devralsin: bu gecis (dogal olarak, ~2sn icinde) bitince,
        # _should_run hala set ise bir sonraki kisa gecisi baslatir --
        # boylece kullaniciya SUREKLI yayin gibi gorunur, ama her tekil
        # hackrf_transfer sureci HER ZAMAN kendi dosyasini bitirip dogal
        # yoldan kapanir.
        self._should_run.set()
        self._loop_thread = threading.Thread(
            target=self._loop_continuation, args=(mod,), daemon=True
        )
        self._loop_thread.start()

        return freq_hz, tx_gain

    def _loop_continuation(self, mod):
        with self.lock:
            proc = self.proc
        if proc is not None:
            proc.wait()  # ilk gecisin dogal olarak bitmesini bekle

        while self._should_run.is_set():
            try:
                cmd, freq_hz, tx_gain = self._build_cmd(mod)
                proc = self._launch(cmd)
            except Exception:
                break
            with self.lock:
                self.proc = proc
            proc.wait()  # ~2 sn sonra dosya biter, surec DOGAL olarak kapanir

        with self.lock:
            self.proc = None

    def stop(self):
        """Donus: True = mevcut gecis kendi dogal suresinde (nazikce) bitti.
        False = zamaninda bitmedi, zorla kapatmak zorunda kaldik -- bu
        durumda cihazda RF sizintisi olabilir, gerekirse fiziksel USB
        cikarma onerilir."""
        self._should_run.clear()

        with self.lock:
            proc = self.proc
        if proc is None or proc.poll() is not None:
            with self.lock:
                self.proc = None
            return True

        # Her gecis kisa (~2sn) oldugu icin, dogal bitisini biraz bekliyoruz
        # -- bu, hicbir zorla kapatmaya GEREK KALMADAN cihazin her zaman
        # duzgun kapanmasini saglar.
        try:
            proc.wait(timeout=3.0)
            graceful = True
        except subprocess.TimeoutExpired:
            graceful = False

        if not graceful:
            pid = proc.pid
            if os.name == "nt":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=5,
                    )
                except Exception:
                    pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass

        with self.lock:
            self.proc = None
        return graceful


class RXWorker(threading.Thread):
    """
    ONEMLI: Bu thread modulasyon etiketini ASLA gormez ve TXController ile
    dogrudan hicbir baglantisi yoktur. Sadece ZMQ'dan ham IQ okur, sinyal
    var mi bakar, kanal filtreler, normalize eder, ozellik cikarir ve
    siniflandirir. Boylece karar mekanizmasina label leakage olmaz.
    """

    def __init__(self, out_queue):
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self._stop_flag = threading.Event()

    def run(self):
        ctx = zmq.Context()
        sock = ctx.socket(zmq.SUB)
        sock.connect(ZMQ_ADDR)
        sock.setsockopt(zmq.SUBSCRIBE, b"")
        sock.setsockopt(zmq.RCVTIMEO, 1000)

        buf = np.array([], dtype=np.complex64)
        last_packet_time = time.monotonic()
        last_status_push = 0.0

        while not self._stop_flag.is_set():
            try:
                raw = sock.recv()
                last_packet_time = time.monotonic()
            except zmq.Again:
                now = time.monotonic()
                if now - last_status_push > 1.0:
                    self.out_queue.put({
                        "type": "waiting",
                        "since_last_packet_sec": now - last_packet_time,
                        "zmq_addr": ZMQ_ADDR,
                    })
                    last_status_push = now
                continue
            except Exception as e:
                self.out_queue.put({"type": "error", "msg": str(e)})
                continue

            chunk = np.frombuffer(raw, dtype=np.complex64)
            buf = np.concatenate([buf, chunk]) if len(buf) else chunk

            if len(buf) < BLOCK_SAMPLES:
                now = time.monotonic()
                if now - last_status_push > 1.0:
                    self.out_queue.put({
                        "type": "filling",
                        "buf_len": len(buf),
                        "block_samples": BLOCK_SAMPLES,
                    })
                    last_status_push = now
                continue
            block = buf[:BLOCK_SAMPLES]
            buf = buf[BLOCK_SAMPLES:]

            try:
                is_signal, margin_db, cfo_hz = _call_wideband_detect(block)
            except Exception as e:
                self.out_queue.put({"type": "error", "msg": f"wideband_detect hata: {e}"})
                continue

            if not is_signal:
                self.out_queue.put({"type": "nosignal", "margin_db": margin_db})
                continue

            try:
                filtered = channelize(block, cfo_hz)
                settle = max(len(filtered) // 10, 1)
                filtered = filtered[settle:]
                norm = normalize_iq(filtered)
                feats = extract_features(norm, RX_SAMPLE_RATE)
                label, prob_digital, _ = classifier_model.classify(feats)
            except Exception as e:
                self.out_queue.put({"type": "error", "msg": f"feature/classify hata: {e}"})
                continue

            self.out_queue.put({
                "type": "result",
                "margin_db": margin_db,
                "cfo_hz": cfo_hz,
                "feats": feats,
                "label": label,
                "prob_digital": prob_digital,
            })

    def stop(self):
        self._stop_flag.set()


class Panel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RF Modulasyon Paneli - ANALOG / DIGITAL")
        self.geometry("580x520")

        self.tx = TXController()
        self.rx_queue = queue.Queue()
        self.rx_worker = RXWorker(self.rx_queue)
        self.rx_worker.start()

        self._build_ui()
        self.after(150, self._poll_rx_queue)

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        frm_top = ttk.Frame(self)
        frm_top.pack(fill="x", **pad)
        ttk.Label(frm_top, text="Modulasyon (AM / FM / BPSK / QPSK):").pack(side="left")
        self.mod_entry = ttk.Entry(frm_top, width=10)
        self.mod_entry.pack(side="left", padx=8)
        self.mod_entry.insert(0, "FM")

        self.start_btn = ttk.Button(frm_top, text="Gonder (Start TX)", command=self.on_start)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(frm_top, text="Durdur (Stop TX)", command=self.on_stop)
        self.stop_btn.pack(side="left", padx=4)

        self.tx_status_var = tk.StringVar(value="TX: bekleniyor")
        ttk.Label(self, textvariable=self.tx_status_var, foreground="gray").pack(anchor="w", **pad)

        ttk.Separator(self).pack(fill="x", **pad)

        frm_stats = ttk.LabelFrame(self, text="RX Canli Istatistikler (etiketi gormeden hesaplaniyor)")
        frm_stats.pack(fill="both", expand=True, **pad)

        self.stats_var = tk.StringVar(value="Sinyal bekleniyor...")
        ttk.Label(
            frm_stats, textvariable=self.stats_var, justify="left", font=("Consolas", 10)
        ).pack(anchor="nw", padx=10, pady=10)

        ttk.Separator(self).pack(fill="x", **pad)

        frm_decision = ttk.Frame(self)
        frm_decision.pack(fill="x", **pad)
        ttk.Label(frm_decision, text="KARAR:", font=("Segoe UI", 14, "bold")).pack(side="left")
        self.decision_var = tk.StringVar(value="-")
        self.decision_label = ttk.Label(
            frm_decision, textvariable=self.decision_var, font=("Segoe UI", 22, "bold")
        )
        self.decision_label.pack(side="left", padx=14)

        self.sent_var = tk.StringVar(value="Gonderilen (senin girdigin): -")
        ttk.Label(self, textvariable=self.sent_var, foreground="gray").pack(anchor="w", **pad)

    def on_start(self):
        mod = self.mod_entry.get().strip().upper()
        if mod not in VALID_MODS:
            messagebox.showerror("Hata", f"Gecersiz modulasyon: {mod}\nGecerli: {VALID_MODS}")
            return
        try:
            freq_hz, tx_gain = self.tx.start(mod, lambda s: self.tx_status_var.set(s))
        except Exception as e:
            messagebox.showerror("TX Hatasi", str(e))
            return
        self.tx_status_var.set(
            f"TX AKTIF: {mod} gonderiliyor | freq={freq_hz/1e6:.4f} MHz | gain={tx_gain} "
            f"(art arda kisa gecisler halinde, surekli)"
        )
        self.sent_var.set(
            f"Gonderilen (senin girdigin): {mod}   <-- bu bilgi RX/karar tarafina VERILMIYOR"
        )

    def on_stop(self):
        graceful = self.tx.stop()
        if graceful:
            self.tx_status_var.set("TX: durduruldu (temiz kapandi)")
        else:
            self.tx_status_var.set(
                "TX: zorla kapatildi -- cihaz nazikce kapanmadi! "
                "Havada hala RF varsa TX HackRF'i USB'den cikar."
            )
            messagebox.showwarning(
                "Zorla Kapatildi",
                "hackrf_transfer nazikce kapanmadi, zorla sonlandirildi.\n"
                "Bu durumda cihaz TX komutunu duzgun almamis olabilir.\n"
                "Havada hala sinyal oldugunu dusunuyorsan, TX HackRF'i "
                "USB'den fiziksel olarak cikar."
            )

    def _poll_rx_queue(self):
        try:
            while True:
                item = self.rx_queue.get_nowait()
                self._handle_rx_item(item)
        except queue.Empty:
            pass
        self.after(150, self._poll_rx_queue)

    def _handle_rx_item(self, item):
        if item["type"] == "waiting":
            self.stats_var.set(
                f"ZMQ'dan veri gelmiyor ({item['since_last_packet_sec']:.0f} sn oldu)\n"
                f"-> RX flowgraph (hackrf_inspector.grc) calisiyor mu?\n"
                f"-> Dinlenen adres: {item['zmq_addr']}"
            )
            self.decision_var.set("-")
            self.decision_label.configure(foreground="gray")
        elif item["type"] == "filling":
            pct = 100.0 * item["buf_len"] / item["block_samples"]
            self.stats_var.set(f"ZMQ baglantisi OK, veri geliyor.\nTampon dolduruluyor: %{pct:.0f}")
        elif item["type"] == "nosignal":
            self.stats_var.set(f"NO SIGNAL  (margin={item['margin_db']:.1f} dB)")
            self.decision_var.set("-")
            self.decision_label.configure(foreground="gray")
        elif item["type"] == "error":
            self.stats_var.set(f"HATA: {item['msg']}")
        elif item["type"] == "result":
            f = item["feats"]
            txt = (
                f"margin      = {item['margin_db']:.1f} dB\n"
                f"cfo         = {item['cfo_hz']/1e6:.4f} MHz\n"
                f"std_amp     = {f['std_amp']:.4f}\n"
                f"kurt_amp    = {f['kurt_amp']:.4f}\n"
                f"std_freq    = {f['std_freq']:.1f} Hz\n"
                f"kurt_freq   = {f['kurt_freq']:.4f}\n"
                f"gamma_max   = {f['gamma_max']:.4f}\n"
                f"abs_C42     = {f['abs_C42']:.4f}\n"
                f"P(DIGITAL)  = {item['prob_digital']*100:.1f}%"
            )
            self.stats_var.set(txt)
            self.decision_var.set(item["label"])
            self.decision_label.configure(
                foreground="#1565c0" if item["label"] == "DIGITAL" else "#2e7d32"
            )

    def on_close(self):
        self.tx.stop()
        self.rx_worker.stop()
        self.destroy()


def main():
    app = Panel()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
