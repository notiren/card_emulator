# Keyboard Routing Solutions for emulator.py

Since `pynput` listener captures all keyboard input, here are practical ways to work around it:

---

## 1. Disable RF IDeas Keyboard Output

Configure RF IDeas to NOT output keyboard events.

- **How it works**: Cards are detected internally, but no keys sent to PC
- **Limitation**: Only works if RF IDeas supports this mode (which you've already set up)

---

## 2. Use a Dedicated USB Keyboard via Hub

Connect a separate USB keyboard just for testing while keeping your main keyboard disconnected.

- **Setup**: Script runs on dedicated hardware, no interference
- **Pros**: Completely clean, no software workarounds needed
- **Cons**: Requires extra hardware

---

## 3. Virtual Keyboard via Software

Use **AutoHotkey** or **KeyboardManager** (Windows) to remap keys. Some tools let you "intercept" at driver level instead of application level.

- **Pros**: Software-only solution
- **Cons**: Complex setup, may conflict with pynput

---

## 4. Run on Separate PC

Run emulator.py on a test machine. Your main PC stays free for other work.

- **Pros**: Most reliable, zero interference
- **Cons**: Requires second computer

---

## 5. Virtual Machine

Run emulator.py in a Windows VM (VirtualBox, Hyper-V, VMware). Host PC unaffected. RF IDeas connects to VM via USB passthrough.

- **Pros**: Clean isolation, no hardware needed
- **Cons**: Setup complexity, VM overhead

---

## 6. Modify pynput to Non-Blocking Mode (Code Change)

Your emulator.py currently blocks forever. You could modify it to:

- Only listen during specific time windows
- Listen with a timeout and release periodically
- Use a toggle key to enable/disable listening

**Example:**
```python
# Current (blocks forever):
def keyboard_listener_thread():
    with Listener(on_press=on_press_handler) as listener:
        listener.join()

# Could become (non-blocking with timeout):
def keyboard_listener_thread():
    listener = Listener(on_press=on_press_handler)
    listener.start()
    while not stop_event.is_set():
        time.sleep(0.1)
    listener.stop()
```

- **Pros**: Single PC solution, no hardware needed
- **Cons**: Requires code changes, less elegant

---

## 7. Use Windows Pause/Resume Feature

Create an AutoHotkey script that:

- Pauses pynput listener when you start typing
- Resumes after X seconds of inactivity

- **Pros**: Automatic, minimal interference
- **Cons**: Slight delay when resuming work

---

## Recommendation (Ranked by Practicality)

1. **Keyboard disabled in RF IDeas + separate USB keyboard** ← Cleanest, you already have RF IDeas config ready
2. **Dedicated test PC** ← If available, most reliable
3. **Virtual Machine** ← Good compromise if no extra PC
4. **Non-blocking listener mode (code modification)** ← If you want single-PC solution

---

## Current Status

`emulator.py` is **production-ready right now**. For immediate testing, use option #1 or #2 - they're the simplest and most reliable approaches.
