import os
import time
import ctypes
import threading


class WAVEFORMATEX(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("wFormatTag", ctypes.c_uint16),
        ("nChannels", ctypes.c_uint16),
        ("nSamplesPerSec", ctypes.c_uint32),
        ("nAvgBytesPerSec", ctypes.c_uint32),
        ("nBlockAlign", ctypes.c_uint16),
        ("wBitsPerSample", ctypes.c_uint16),
        ("cbSize", ctypes.c_uint16),
    ]


class WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_void_p),
        ("dwBufferLength", ctypes.c_uint32),
        ("dwBytesRecorded", ctypes.c_uint32),
        ("dwUser", ctypes.c_size_t),
        ("dwFlags", ctypes.c_uint32),
        ("dwLoops", ctypes.c_uint32),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_size_t),
    ]


class WaveOutPlayer:
    """Streams 16-bit 44.1kHz stereo PCM to Windows WaveOut with instant volume control."""

    WHDR_DONE = 0x00000001
    WHDR_PREPARED = 0x00000002

    def __init__(self, sample_rate=44100, channels=2, num_buffers=8):
        self.sample_rate = sample_rate
        self.channels = channels
        self.num_buffers = num_buffers
        self.h_wave = None
        self.lock = threading.Lock()
        self.volume = 0.7
        self.active = False
        self.slots = []
        self._winmm = None

        if os.name == "nt":
            try:
                w = ctypes.windll.winmm
                w.waveOutOpen.argtypes = [
                    ctypes.POINTER(ctypes.c_void_p),
                    ctypes.c_uint,
                    ctypes.POINTER(WAVEFORMATEX),
                    ctypes.c_size_t,
                    ctypes.c_size_t,
                    ctypes.c_uint,
                ]
                w.waveOutOpen.restype = ctypes.c_uint
                w.waveOutPrepareHeader.argtypes = [ctypes.c_void_p, ctypes.POINTER(WAVEHDR), ctypes.c_uint]
                w.waveOutPrepareHeader.restype = ctypes.c_uint
                w.waveOutWrite.argtypes = [ctypes.c_void_p, ctypes.POINTER(WAVEHDR), ctypes.c_uint]
                w.waveOutWrite.restype = ctypes.c_uint
                w.waveOutUnprepareHeader.argtypes = [ctypes.c_void_p, ctypes.POINTER(WAVEHDR), ctypes.c_uint]
                w.waveOutUnprepareHeader.restype = ctypes.c_uint
                w.waveOutReset.argtypes = [ctypes.c_void_p]
                w.waveOutReset.restype = ctypes.c_uint
                w.waveOutClose.argtypes = [ctypes.c_void_p]
                w.waveOutClose.restype = ctypes.c_uint
                w.waveOutSetVolume.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
                w.waveOutSetVolume.restype = ctypes.c_uint
                self._winmm = w
            except Exception:
                self._winmm = None

    def open(self):
        if not self._winmm:
            return False
        self.stop()
        with self.lock:
            wfx = WAVEFORMATEX(
                wFormatTag=1,
                nChannels=self.channels,
                nSamplesPerSec=self.sample_rate,
                nAvgBytesPerSec=self.sample_rate * self.channels * 2,
                nBlockAlign=self.channels * 2,
                wBitsPerSample=16,
                cbSize=0,
            )
            h = ctypes.c_void_p()
            res = self._winmm.waveOutOpen(ctypes.byref(h), 0xFFFFFFFF, ctypes.byref(wfx), 0, 0, 0)
            if res != 0:
                return False
            self.h_wave = h
            self.active = True
            self.slots = [[None, None, False] for _ in range(self.num_buffers)]
            self._apply_volume_locked()
            return True

    def set_volume(self, vol_float):
        self.volume = max(0.0, min(1.0, float(vol_float)))
        with self.lock:
            self._apply_volume_locked()

    def _apply_volume_locked(self):
        if self._winmm and self.h_wave:
            v = int(self.volume * 0xFFFF)
            dw = (v << 16) | v
            try:
                self._winmm.waveOutSetVolume(self.h_wave, dw)
            except Exception:
                pass

    def write(self, data_bytes):
        if not self._winmm or not self.active or not data_bytes:
            return False
        while self.active:
            with self.lock:
                if not self.active or not self.h_wave:
                    return False
                for slot in self.slots:
                    hdr, buf, in_use = slot
                    if not in_use or (hdr and (hdr.dwFlags & self.WHDR_DONE)):
                        if hdr and (hdr.dwFlags & self.WHDR_PREPARED):
                            self._winmm.waveOutUnprepareHeader(
                                self.h_wave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
                            )
                        new_buf = ctypes.create_string_buffer(data_bytes, len(data_bytes))
                        new_hdr = WAVEHDR(
                            lpData=ctypes.cast(new_buf, ctypes.c_void_p).value,
                            dwBufferLength=len(data_bytes),
                            dwFlags=0,
                        )
                        self._winmm.waveOutPrepareHeader(
                            self.h_wave, ctypes.byref(new_hdr), ctypes.sizeof(WAVEHDR)
                        )
                        self._winmm.waveOutWrite(
                            self.h_wave, ctypes.byref(new_hdr), ctypes.sizeof(WAVEHDR)
                        )
                        slot[0] = new_hdr
                        slot[1] = new_buf
                        slot[2] = True
                        return True
            time.sleep(0.01)
        return False

    def stop(self):
        self.active = False
        if not self._winmm:
            return
        with self.lock:
            if self.h_wave:
                try:
                    self._winmm.waveOutReset(self.h_wave)
                    for hdr, _, _ in self.slots:
                        if hdr and (hdr.dwFlags & self.WHDR_PREPARED):
                            self._winmm.waveOutUnprepareHeader(
                                self.h_wave, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR)
                            )
                    self._winmm.waveOutClose(self.h_wave)
                except Exception:
                    pass
                self.h_wave = None
                self.slots = []
