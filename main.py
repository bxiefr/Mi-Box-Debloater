import os
import subprocess
import sys
import time

LANGS = {
    "tr": {
        "title": "Mi Box Debloater v1.0.0",
        "lang_name": "Turkce",
        "banner": "=== MI BOX DEBLOATER & OPTIMIZER ===",
        "ip_prompt": "Mi Box IP adresini girin (Orn: 192.168.1.45): ",
        "connecting": "Cihaza baglaniliyor...",
        "connected": "Baglanti basarili!",
        "conn_error": (
            "Baglanti kurulamadi! IP ve USB/Ag Hata Ayiklamayi kontrol edin."
        ),
        "cleaning": "Gereksiz paketler temizleniyor...",
        "opt_anim": "Arayuz animasyonlari hizlandiriliyor (0.5x)...",
        "opt_dex": "Sistem paketleri optimize ediliyor (dexopt)...",
        "success": "ISLEM TAMAMLANDI! Cihaz yeniden baslatiliyor...",
        "press_exit": "Cikmak icin ENTER tusuna basin...",
    },
    "en": {
        "title": "Mi Box Debloater v1.0.0",
        "lang_name": "English",
        "banner": "=== MI BOX DEBLOATER & OPTIMIZER ===",
        "ip_prompt": "Enter Mi Box IP address (Ex: 192.168.1.45): ",
        "connecting": "Connecting to device...",
        "connected": "Connection successful!",
        "conn_error": (
            "Connection failed! Check IP and Network Debugging settings."
        ),
        "cleaning": "Cleaning bloatware packages...",
        "opt_anim": "Speeding up UI animations (0.5x)...",
        "opt_dex": "Optimizing system packages (dexopt)...",
        "success": "PROCESS COMPLETED! Rebooting device...",
        "press_exit": "Press ENTER to exit...",
    },
}

PACKAGES = [
    "com.mitv.tvhome.michannel",
    "com.xiaomi.mitv.updateservice",
    "com.xiaomi.mibox.gamecenter",
    "com.xiaomi.tv.recommend",
    "mitv.service",
    "com.google.android.feedback",
    "com.google.android.partnersetup",
    "com.google.android.syncadapters.calendar",
    "com.google.android.syncadapters.contacts",
    "com.google.android.tts",
    "com.google.android.videos",
    "com.google.android.music",
    "com.google.android.play.games",
    "com.google.android.marvin.talkback",
    "com.amazon.amazonvideo.livingroom",
    "com.disney.disneyplus",
    "com.apple.atve.androidtv.appletv",
]


def clear_screen():
  os.system("cls" if os.name == "nt" else "clear")


def loading_anim(text, duration=2):
  chars = ["|", "/", "-", "\\"]
  end_time = time.time() + duration
  i = 0
  while time.time() < end_time:
    sys.stdout.write(f"\r{text} {chars[i % len(chars)]}")
    sys.stdout.flush()
    time.sleep(0.1)
    i += 1
  sys.stdout.write(f"\r{text} [OK]     \n")
  sys.stdout.flush()


def run_cmd(cmd):
  try:
    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()
  except Exception:
    return ""


def select_language():
  clear_screen()
  print("=== LANGUAGE SELECTION / DIL SECIMI ===")
  print("1. Turkce")
  print("2. English")
  choice = input("Choice / Secim (1/2): ").strip()
  if choice == "2":
    return "en"
  return "tr"


def main():
  lang_key = select_language()
  t = LANGS[lang_key]

  clear_screen()
  print(t["banner"])
  ip = input(t["ip_prompt"]).strip()
  if not ip:
    ip = "127.0.0.1"

  print(f"\n{t['connecting']}")
  run_cmd("adb kill-server")
  run_cmd("adb start-server")
  run_cmd(f"adb connect {ip}")
  loading_anim(t["connecting"], 2.5)

  devices_output = run_cmd("adb devices")
  if ip not in devices_output or "device" not in devices_output:
    print(f"\n{t['conn_error']}")
    input(t["press_exit"])
    sys.exit(1)

  print(f"\n{t['connected']}")
  time.sleep(1)

  clear_screen()
  print(t["banner"])
  print(f"\n{t['cleaning']}")
  for pkg in PACKAGES:
    sys.stdout.write(f"-> {pkg}... ")
    sys.stdout.flush()
    run_cmd(f"adb shell pm uninstall -k --user 0 {pkg}")
    print("[DONE]")
    time.sleep(0.05)

  print(f"\n{t['opt_anim']}")
  run_cmd("adb shell settings put global window_animation_scale 0.5")
  run_cmd("adb shell settings put global transition_animation_scale 0.5")
  run_cmd("adb shell settings put global animator_duration_scale 0.5")
  loading_anim("...", 1.5)

  print(f"\n{t['opt_dex']}")
  run_cmd("adb shell cmd package bg-dexopt-job")
  loading_anim("...", 2)

  print(f"\n{t['success']}")
  run_cmd("adb reboot")
  input(f"\n{t['press_exit']}")


if __name__ == "__main__":
  main()
