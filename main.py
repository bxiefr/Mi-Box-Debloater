import argparse
import ipaddress
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

__version__ = "0.0.0-dev"
VERSION = os.environ.get("MIBOX_VERSION", "").strip().lstrip("vV") or __version__

APP_NAME = "Mi Box Debloater"
LOG_FILE = "mibox_debloater.log"
BACKUP_PREFIX = "mibox_backup_"
DEFAULT_ADB_PORT = 5555

ANIM_KEYS = (
    "window_animation_scale",
    "transition_animation_scale",
    "animator_duration_scale",
)

LANGS = {
    "tr": {
        "lang_name": "Türkçe",
        "title": "{app} v{version}",
        "banner": "=== MI BOX DEBLOATER & OPTİMİZER ===",
        "menu": "1) Temizle ve optimize et\n2) Geri yükle (yedekten)\n3) Çıkış",
        "menu_prompt": "Seçim (1/2/3): ",
        "ip_prompt": "Mi Box IP adresini girin (Örn: 192.168.1.45): ",
        "bad_ip": "Geçersiz IP adresi: {ip}",
        "adb_missing": "ADB bulunamadı! Platform-tools kurup PATH'e ekleyin.",
        "connecting": "Cihaza bağlanılıyor ({target})...",
        "connected": "Bağlantı başarılı!",
        "unauthorized": "Cihaz yetkilendirilmemiş. TV ekranındaki USB/Ağ hata ayıklama izin penceresini onaylayın.",
        "conn_error": "Bağlantı kurulamadı! IP adresini ve Ağ Hata Ayıklama ayarını kontrol edin.",
        "scanning": "Yüklü paketler taranıyor...",
        "plan_header": "Kaldırılacak paketler:",
        "plan_empty": "Kaldırılacak paket bulunamadı (hepsi zaten temiz).",
        "risk_safe": "güvenli",
        "risk_caution": "dikkat",
        "skipped_protected": "Korumalı paket atlandı: {pkg}",
        "confirm": "{n} paket kaldırılacak. Devam edilsin mi? (e/h): ",
        "yes_chars": "eEyY",
        "aborted": "İptal edildi.",
        "backup_saved": "Yedek kaydedildi: {file}",
        "cleaning": "Gereksiz paketler temizleniyor...",
        "pkg_ok": "[TAMAM]",
        "pkg_fail": "[HATA] {reason}",
        "pkg_dry": "[DENEME] kaldırılmadı",
        "summary": "Özet: {ok} kaldırıldı, {fail} hata, {skip} atlandı.",
        "opt_anim": "Arayüz animasyonları hızlandırılıyor ({scale}x)...",
        "opt_dex": "Sistem paketleri optimize ediliyor (dexopt)...",
        "dex_slow": "Bu işlem birkaç dakika sürebilir.",
        "restore_none": "Geri yüklenecek yedek dosyası bulunamadı.",
        "restore_using": "Yedek kullanılıyor: {file}",
        "restore_start": "Paketler geri yükleniyor...",
        "restore_anim": "Animasyon ayarları eski haline getiriliyor...",
        "success": "İŞLEM TAMAMLANDI!",
        "rebooting": "Cihaz yeniden başlatılıyor...",
        "press_exit": "Çıkmak için ENTER tuşuna basın...",
        "lang_select": "=== DİL SEÇİMİ / LANGUAGE SELECTION ===",
        "lang_prompt": "Seçim / Choice (1/2): ",
        "dry_notice": "DENEME MODU: Cihazda hiçbir değişiklik yapılmayacak.",
    },
    "en": {
        "lang_name": "English",
        "title": "{app} v{version}",
        "banner": "=== MI BOX DEBLOATER & OPTIMIZER ===",
        "menu": "1) Debloat and optimize\n2) Restore (from backup)\n3) Exit",
        "menu_prompt": "Choice (1/2/3): ",
        "ip_prompt": "Enter Mi Box IP address (Ex: 192.168.1.45): ",
        "bad_ip": "Invalid IP address: {ip}",
        "adb_missing": "ADB not found! Install platform-tools and add it to PATH.",
        "connecting": "Connecting to device ({target})...",
        "connected": "Connection successful!",
        "unauthorized": "Device not authorized. Accept the debugging prompt on the TV screen.",
        "conn_error": "Connection failed! Check the IP address and Network Debugging setting.",
        "scanning": "Scanning installed packages...",
        "plan_header": "Packages to be removed:",
        "plan_empty": "No packages to remove (everything is already clean).",
        "risk_safe": "safe",
        "risk_caution": "caution",
        "skipped_protected": "Protected package skipped: {pkg}",
        "confirm": "{n} packages will be removed. Continue? (y/n): ",
        "yes_chars": "yY",
        "aborted": "Aborted.",
        "backup_saved": "Backup saved: {file}",
        "cleaning": "Cleaning bloatware packages...",
        "pkg_ok": "[DONE]",
        "pkg_fail": "[FAIL] {reason}",
        "pkg_dry": "[DRY-RUN] not removed",
        "summary": "Summary: {ok} removed, {fail} failed, {skip} skipped.",
        "opt_anim": "Speeding up UI animations ({scale}x)...",
        "opt_dex": "Optimizing system packages (dexopt)...",
        "dex_slow": "This may take a few minutes.",
        "restore_none": "No backup file found to restore.",
        "restore_using": "Using backup: {file}",
        "restore_start": "Restoring packages...",
        "restore_anim": "Restoring animation settings...",
        "success": "PROCESS COMPLETED!",
        "rebooting": "Rebooting device...",
        "press_exit": "Press ENTER to exit...",
        "lang_select": "=== LANGUAGE SELECTION / DİL SEÇİMİ ===",
        "lang_prompt": "Choice / Seçim (1/2): ",
        "dry_notice": "DRY-RUN: no changes will be made to the device.",
    },
}

PACKAGES = {
    "Xiaomi": [
        ("com.mitv.tvhome.michannel", "safe"),
        ("com.xiaomi.mibox.gamecenter", "safe"),
        ("com.xiaomi.tv.recommend", "safe"),
        ("com.xiaomi.mitv.updateservice", "caution"),
        ("mitv.service", "caution"),
    ],
    "Google": [
        ("com.google.android.feedback", "safe"),
        ("com.google.android.partnersetup", "safe"),
        ("com.google.android.syncadapters.calendar", "safe"),
        ("com.google.android.syncadapters.contacts", "safe"),
        ("com.google.android.videos", "safe"),
        ("com.google.android.music", "safe"),
        ("com.google.android.play.games", "safe"),
        ("com.google.android.tts", "caution"),
        ("com.google.android.marvin.talkback", "caution"),
    ],
    "Streaming": [
        ("com.amazon.amazonvideo.livingroom", "safe"),
        ("com.disney.disneyplus", "safe"),
        ("com.apple.atve.androidtv.appletv", "safe"),
    ],
}

PROTECTED = {
    "com.google.android.gms",
    "com.google.android.gsf",
    "com.android.vending",
    "com.google.android.tvlauncher",
    "com.google.android.leanbacklauncher",
    "com.android.settings",
    "com.android.systemui",
    "com.android.providers.settings",
    "com.google.android.tv.remote.service",
    "android",
}


class Console:
    def __init__(self, lang):
        self.t_map = LANGS[lang]

    def t(self, key, **kw):
        text = self.t_map[key]
        return text.format(**kw) if kw else text

    def say(self, key="", **kw):
        print(self.t(key, **kw) if key else "")


class Spinner:
    FRAMES = "|/-\\"

    def __init__(self, text):
        self.text = text
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            sys.stdout.write(f"\r{self.text} {self.FRAMES[i % 4]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()
        sys.stdout.write(f"\r{self.text} [OK]     \n")
        sys.stdout.flush()


def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


def clear_screen():
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def adb(args, serial=None, timeout=30):
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        out = (r.stdout or "").strip()
        logging.info("%s -> rc=%s out=%s", " ".join(cmd), r.returncode, out[:300])
        return r.returncode, out
    except subprocess.TimeoutExpired:
        logging.error("TIMEOUT: %s", " ".join(cmd))
        return 124, "timeout"
    except OSError as exc:
        logging.error("ERROR: %s (%s)", " ".join(cmd), exc)
        return 1, str(exc)


def normalize_target(raw):
    raw = raw.strip()
    host, _, port = raw.partition(":")
    try:
        ipaddress.ip_address(host)
        port_num = int(port) if port else DEFAULT_ADB_PORT
        if not 1 <= port_num <= 65535:
            return None
    except ValueError:
        return None
    return f"{host}:{port_num}"


def device_state(target):
    _, out = adb(["devices"])
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == target:
            return parts[1]
    return None


def get_installed(serial):
    _, out = adb(["shell", "pm", "list", "packages"], serial, timeout=60)
    return {
        line.split(":", 1)[1].strip()
        for line in out.splitlines()
        if line.startswith("package:")
    }


def get_setting(serial, key):
    _, out = adb(["shell", "settings", "get", "global", key], serial)
    return out if out and out != "null" else None


def put_setting(serial, key, value):
    return adb(["shell", "settings", "put", "global", key, str(value)], serial)


def ask_yes(con, key, **kw):
    answer = input(con.t(key, **kw)).strip()
    return bool(answer) and answer[0] in con.t("yes_chars")


def build_plan(con, installed, safe_only):
    plan = []
    for category, items in PACKAGES.items():
        for pkg, risk in items:
            if pkg in PROTECTED:
                con.say("skipped_protected", pkg=pkg)
                continue
            if safe_only and risk != "safe":
                continue
            if pkg in installed:
                plan.append((category, pkg, risk))
    return plan


def do_debloat(con, serial, args):
    con.say("scanning")
    installed = get_installed(serial)
    plan = build_plan(con, installed, args.safe_only)
    total_candidates = sum(len(v) for v in PACKAGES.values())
    skipped = total_candidates - len(plan)

    if not plan:
        con.say("plan_empty")
        return

    con.say()
    con.say("plan_header")
    for category, pkg, risk in plan:
        print(f"  [{category}] {pkg}  ({con.t('risk_' + risk)})")
    con.say()

    if args.dry_run:
        con.say("dry_notice")
    elif not args.yes and not ask_yes(con, "confirm", n=len(plan)):
        con.say("aborted")
        return

    backup = {
        "version": VERSION,
        "created": datetime.now().isoformat(timespec="seconds"),
        "serial": serial,
        "removed": [],
        "animations": {k: get_setting(serial, k) for k in ANIM_KEYS},
    }

    con.say()
    con.say("cleaning")
    ok = fail = 0
    for _, pkg, _ in plan:
        sys.stdout.write(f"-> {pkg}... ")
        sys.stdout.flush()
        if args.dry_run:
            print(con.t("pkg_dry"))
            continue
        rc, out = adb(["shell", "pm", "uninstall", "-k", "--user", "0", pkg], serial)
        if rc == 0 and "Success" in out:
            print(con.t("pkg_ok"))
            backup["removed"].append(pkg)
            ok += 1
        else:
            print(con.t("pkg_fail", reason=out.splitlines()[-1] if out else "?"))
            fail += 1

    con.say("summary", ok=ok, fail=fail, skip=skipped)

    if args.dry_run:
        return

    if backup["removed"]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path(f"{BACKUP_PREFIX}{serial.replace(':', '_')}_{stamp}.json")
        path.write_text(json.dumps(backup, indent=2), encoding="utf-8")
        con.say("backup_saved", file=path)

    if not args.no_optimize:
        con.say()
        con.say("opt_anim", scale=args.anim_scale)
        for key in ANIM_KEYS:
            put_setting(serial, key, args.anim_scale)

        con.say()
        con.say("opt_dex")
        con.say("dex_slow")
        with Spinner("..."):
            adb(["shell", "cmd", "package", "bg-dexopt-job"], serial, timeout=900)


def find_latest_backup(serial, explicit):
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    prefix = f"{BACKUP_PREFIX}{serial.replace(':', '_')}_"
    files = sorted(Path(".").glob(f"{prefix}*.json"))
    if not files:
        files = sorted(Path(".").glob(f"{BACKUP_PREFIX}*.json"))
    return files[-1] if files else None


def do_restore(con, serial, args):
    path = find_latest_backup(serial, args.backup_file)
    if not path:
        con.say("restore_none")
        return
    con.say("restore_using", file=path)
    data = json.loads(path.read_text(encoding="utf-8"))

    con.say("restore_start")
    ok = fail = 0
    for pkg in data.get("removed", []):
        sys.stdout.write(f"-> {pkg}... ")
        sys.stdout.flush()
        rc, out = adb(
            ["shell", "cmd", "package", "install-existing", "--user", "0", pkg],
            serial,
        )
        if rc == 0 and "installed" in out.lower():
            print(con.t("pkg_ok"))
            ok += 1
        else:
            print(con.t("pkg_fail", reason=out.splitlines()[-1] if out else "?"))
            fail += 1
    con.say("summary", ok=ok, fail=fail, skip=0)

    con.say("restore_anim")
    for key, value in data.get("animations", {}).items():
        if value is None:
            adb(["shell", "settings", "delete", "global", key], serial)
        else:
            put_setting(serial, key, value)


def connect(con, ip_arg):
    if shutil.which("adb") is None:
        con.say("adb_missing")
        return None

    raw = ip_arg or input(con.t("ip_prompt")).strip()
    target = normalize_target(raw)
    if not target:
        con.say("bad_ip", ip=raw)
        return None

    con.say("connecting", target=target)
    adb(["start-server"])
    with Spinner(con.t("connecting", target=target)):
        adb(["connect", target], timeout=15)
        state = device_state(target)

    if state == "unauthorized":
        con.say("unauthorized")
        return None
    if state != "device":
        con.say("conn_error")
        return None

    con.say("connected")
    return target


def select_language(forced):
    if forced:
        return forced
    clear_screen()
    print(LANGS["tr"]["lang_select"])
    print("1. Türkçe")
    print("2. English")
    return "en" if input(LANGS["tr"]["lang_prompt"]).strip() == "2" else "tr"


def parse_args():
    p = argparse.ArgumentParser(description=f"{APP_NAME} v{VERSION}")
    p.add_argument("--version", action="version", version=f"{APP_NAME} v{VERSION}")
    p.add_argument("--lang", choices=sorted(LANGS), help="tr | en")
    p.add_argument("--ip", help="Mi Box IP (veya IP:port)")
    p.add_argument("--dry-run", action="store_true", help="Hicbir sey degistirme / change nothing")
    p.add_argument("--restore", action="store_true", help="Yedekten geri yukle / restore from backup")
    p.add_argument("--backup-file", help="Geri yukleme icin yedek dosyasi")
    p.add_argument("--safe-only", action="store_true", help="Sadece 'guvenli' paketleri kaldir")
    p.add_argument("--no-optimize", action="store_true", help="Animasyon/dexopt atla")
    p.add_argument("--anim-scale", default="0.5", help="Animasyon olcegi (varsayilan 0.5)")
    p.add_argument("--no-reboot", action="store_true", help="Sonunda yeniden baslatma")
    p.add_argument("-y", "--yes", action="store_true", help="Onay sorma / no prompts")
    return p.parse_args()


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    setup_logging()
    args = parse_args()
    interactive = not args.yes
    lang = select_language(args.lang) if (interactive or not args.lang) else args.lang
    con = Console(lang)

    clear_screen()
    print(con.t("title", app=APP_NAME, version=VERSION))
    con.say("banner")
    logging.info("Start %s v%s lang=%s args=%s", APP_NAME, VERSION, lang, vars(args))

    serial = connect(con, args.ip)
    if not serial:
        if interactive:
            input(con.t("press_exit"))
        sys.exit(1)

    mode = "restore" if args.restore else "debloat"
    if interactive and not args.restore and not args.dry_run and args.ip is None:
        con.say()
        con.say("menu")
        choice = input(con.t("menu_prompt")).strip()
        if choice == "3":
            return
        mode = "restore" if choice == "2" else "debloat"

    clear_screen()
    print(con.t("title", app=APP_NAME, version=VERSION))
    con.say("banner")

    if mode == "restore":
        do_restore(con, serial, args)
    else:
        do_debloat(con, serial, args)

    con.say()
    con.say("success")
    if not args.dry_run and not args.no_reboot and mode == "debloat":
        con.say("rebooting")
        adb(["reboot"], serial)

    if interactive:
        input(f"\n{con.t('press_exit')}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(130)
