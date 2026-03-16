# Windows 11 Clean Setup Guide
## Zero bloat, maximum performance & battery, no telemetry

---

## Phase 1: Install Windows 11

1. Download the official Windows 11 ISO from **microsoft.com/software-download/windows11**
2. Create a bootable USB using **Rufus** (rufus.ie) — it's free and portable
3. In Rufus, after selecting the ISO, it will ask you about Windows customizations. **Check these boxes:**
   - Remove requirement for online Microsoft account
   - Disable data collection
   - Remove requirement for 4GB RAM, Secure Boot, and TPM (if needed for your Omen)
4. Boot from USB and install Windows
5. During setup: **choose "I don't have internet"** or **"Limited setup"** to create a **local account**
6. Pick a username and password — no Microsoft account needed

---

## Phase 2: First Boot — Before Anything Else

Don't install anything yet. Do these first:

### Connect to Wi-Fi
You need internet for the next steps, but Windows will try to push updates and bloat. That's fine — we'll clean it all up.

### Open PowerShell as Admin
- Right-click the Start button → **Terminal (Admin)**

### Run Chris Titus WinUtil
Paste this command and press Enter:

```
irm christitus.com/win | iex
```

This opens a graphical tool. Here's what to do in it:

#### Tweaks Tab (the main one)
Select the **"Desktop"** preset at the top, then also manually check:

- ✅ Disable Telemetry
- ✅ Disable Wi-Fi Sense
- ✅ Disable Activity History
- ✅ Disable Location Tracking
- ✅ Disable Copilot
- ✅ Remove Copilot
- ✅ Disable GameDVR (saves battery)
- ✅ Disable Hibernation (if you don't use it — saves disk space)
- ✅ Set Services to Manual
- ✅ Disable Unnecessary Startup Apps
- ✅ Remove Microsoft Edge (optional — only if you'll use Firefox/Brave)

Click **"Run Tweaks"** and wait for it to finish.

#### Updates Tab
- Select **"Security (Recommended)"** — this gives you security patches only, no feature updates that re-add bloat

---

## Phase 3: Remove Bloat Apps

Still in WinUtil, or manually via Settings → Apps → Installed Apps, **uninstall**:

- Clipchamp
- Microsoft News
- Microsoft To Do (unless you use it)
- Solitaire Collection
- Xbox apps (if you don't game on Xbox)
- Weather
- Get Help
- Tips
- Power Automate
- OneDrive (right-click taskbar icon → Quit → then uninstall from Settings)
- Teams (free/personal version)
- Any other apps you didn't ask for

---

## Phase 4: Privacy Lockdown

### Install O&O ShutUp10++
Download from **oo-software.com/en/shutup10** (free, portable, no install needed).

Open it and apply the **"Recommended"** settings. These disable:

- Advertising ID
- Typing/inking data collection
- Diagnostic data
- Tailored experiences
- App launch tracking
- Suggested content
- Timeline / Activity History

You can also apply the "Somewhat recommended" settings if you want maximum privacy. Read each one — they're clearly explained.

### Block Telemetry Domains (Optional but Effective)
Open Notepad as Admin, then open the file: `C:\Windows\System32\drivers\etc\hosts`

Add these lines at the bottom:

```
0.0.0.0 vortex.data.microsoft.com
0.0.0.0 settings-win.data.microsoft.com
0.0.0.0 watson.telemetry.microsoft.com
0.0.0.0 telemetry.microsoft.com
0.0.0.0 activity.windows.com
0.0.0.0 self.events.data.microsoft.com
```

Save the file. This blocks Windows from sending telemetry data even if some setting gets re-enabled by an update.

---

## Phase 5: Performance & Battery Optimization

### Power Settings
- Settings → System → Power & Battery
- Set Power Mode to **"Best power efficiency"** for battery, or **"Balanced"** for plugged in
- Set Screen off: 5 min (battery), 15 min (plugged in)
- Set Sleep: 15 min (battery), 30 min (plugged in)

### Startup Apps
- Open Task Manager (Ctrl+Shift+Esc) → Startup tab
- Disable everything you don't need starting at boot
- Keep: your antivirus (if any), audio drivers
- Disable: OneDrive, Teams, Spotify, Edge, anything else

### Visual Effects (Small Speed Boost)
- Search "Adjust the appearance and performance of Windows"
- Select **"Adjust for best performance"**
- Then re-check these two for a usable look:
  - ✅ Show thumbnails instead of icons
  - ✅ Smooth edges of screen fonts

### Disable Search Indexing (Saves Battery & Disk)
- Open Services (search "services.msc")
- Find **"Windows Search"** → double-click → set to **Disabled**
- This stops background indexing. You can still search, just slightly slower.

---

## Phase 6: Install Your Essential Software

Now that Windows is clean, install what you actually need:

- **Browser**: Firefox or Brave (with uBlock Origin)
- **Code editor**: VS Code or your preferred IDE
- **Terminal**: Windows Terminal (already included)
- **Password manager**: Bitwarden
- **Minecraft**: Download the launcher, sign in with your Microsoft account inside it
- **Git**: git-scm.com
- **WSL2** (optional): If you want a Linux terminal inside Windows, run:
  ```
  wsl --install
  ```
  This gives you Ubuntu inside Windows — great for coding.

---

## Phase 7: Maintenance Rules

To keep your system clean going forward:

1. **Never sign into Windows with a Microsoft account** — always use local
2. **After major Windows updates**, re-run WinUtil and O&O ShutUp10 — updates sometimes re-enable telemetry
3. **Check startup apps** every few weeks — new software loves to add itself there
4. **Don't install "PC cleaner" apps** — they're bloat themselves. Windows doesn't need them.
5. **Use WinUtil's update settings** to stay on security-only updates

---

## Quick Reference

| Tool | What it does | Where to get it |
|------|-------------|----------------|
| WinUtil | Debloat + tweak Windows | `irm christitus.com/win \| iex` in PowerShell |
| O&O ShutUp10++ | Privacy toggles | oo-software.com/en/shutup10 |
| Rufus | Create bootable USB | rufus.ie |
| Bitwarden | Password + passkey manager | bitwarden.com |
