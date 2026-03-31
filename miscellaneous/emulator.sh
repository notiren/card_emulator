#!/system/bin/sh
# RFID Card Emulator - Android Shell Version
# Detects devices via PID/VID and runs emulation sequence

# --- CONFIGURATION ---
NUM_CARDS=100          # set low for testing; change back to 4473924 for full run
START_VALUE_HEX=0x337AF8
STEP_SIZE_HEX=0x000003
START_VALUE=$((16#337AF8))  # Convert hex to decimal
STEP_SIZE=$((16#000003))    # Convert hex to decimal
KEY_TYPE="EM4100/32"
UID_LENGTH=10
EMULATION_DELAY=0.0
DELAY_BETWEEN_CARDS=0.0
RFIDEAS_TIMEOUT=1
READER_TIMEOUT=2.5
READER_RETRIES=40
RESET_INTERVAL=40
CONSECUTIVE_NODATA_LIMIT=8  # stop/alert if too many loops without detected card
LOG_FILE="emulator_log.csv"
TEMP_DIR="/data/local/tmp"
RFIDEAS_EVENT="/dev/input/event11"  # RFIDEAs keyboard event device
# Device port lock overrides (set non-empty to force hard-coded hardware mapping)
FORCE_FLIPPER_PORT="/dev/ttyACM2"  # no real emulation currently, test only
FORCE_READER_PORT="/dev/ttyACM1"   # should be HelloID reader
# Preferred defaults (set to what you have):
FLIPPER_DEFAULT="/dev/ttyACM2"   # Flipper device path (the emulator port)
READER_DEFAULT="/dev/ttyACM1"    # HelloID reader path (the packet reader)
# Note: FIFOs removed - using simplified architecture

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# --- UTILITY FUNCTIONS ---

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
}

find_device_by_vid_pid() {
    local vid=$1
    local pid=$2
    local port_to_avoid=$3
    local vid_hex=$(printf "%04x" "$vid")
    local pid_hex=$(printf "%04x" "$pid")
    
    # Try to find device via sysfs
    if [ -d "/sys/bus/usb/devices" ]; then
        for device in /sys/bus/usb/devices/*/; do
            if [ -f "${device}idVendor" ]; then
                local dev_vid=$(cat "${device}idVendor" 2>/dev/null)
                local dev_pid=$(cat "${device}idProduct" 2>/dev/null)
                if [ "$dev_vid" = "$vid_hex" ] && [ "$dev_pid" = "$pid_hex" ]; then
                    # Found matching device, try to get serial port
                    for port in /dev/ttyUSB* /dev/ttyACM*; do
                        if [ -e "$port" ]; then
                            if [ -n "$port_to_avoid" ] && [ "$port" = "$port_to_avoid" ]; then
                                continue
                            fi
                            echo "$port"
                            return 0
                        fi
                    done
                fi
            fi
        done
    fi
    
    return 1
}

check_flipper_device() {
    log_msg "Searching for Flipper device (VID: 0x0483, PID: 0x5740)..."

    if [ -n "$FORCE_FLIPPER_PORT" ] && [ -e "$FORCE_FLIPPER_PORT" ]; then
        log_msg "${GREEN}✓ Using forced Flipper port: $FORCE_FLIPPER_PORT${NC}"
        flipper_port="$FORCE_FLIPPER_PORT"
    else
        local flipper_port=$(find_device_by_vid_pid 0x0483 0x5740)
        if [ -z "$flipper_port" ] || [ "$flipper_port" = "/dev/ttyACM0" ]; then
            # prefer your actual Flipper port
            flipper_port="$FLIPPER_DEFAULT"
            log_msg "${RED}Flipper auto-detection gave /dev/ttyACM0 or failed; using default $flipper_port${NC}"
        else
            log_msg "${GREEN}✓ Flipper detected on $flipper_port${NC}"
        fi
    fi
    
    if [ ! -e "$flipper_port" ]; then
        log_msg "${RED}✗ Error: $flipper_port does not exist${NC}"
        log_msg "Available USB devices:"
        ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || log_msg "No USB devices found"
        log_msg ""
        echo -n "Enter Flipper port manually (default $FLIPPER_DEFAULT): "
        read -r flipper_port
        flipper_port=${flipper_port:-$FLIPPER_DEFAULT}
    fi

    # Configure serial port for Flipper (230400 baud, 8N1)
    if command -v stty >/dev/null 2>&1; then
        stty -F "$flipper_port" 230400 cs8 -cstopb -parenb 2>/dev/null || \
        stty -f "$flipper_port" 230400 cs8 -cstopb -parenb 2>/dev/null || \
        log_msg "Warning: Could not configure Flipper serial port with stty"
        log_msg "Configured $flipper_port to 230400 baud"
    else
        log_msg "Warning: stty not available, skipping Flipper port configuration"
    fi

    log_msg "${GREEN}✓ Flipper port ready: $flipper_port${NC}"
    echo "$flipper_port"
    return 0
}

check_reader_device() {
    log_msg "Searching for Reader device (VID: 0x1d6b, PID: 0x4944)..."

    if [ -n "$FORCE_READER_PORT" ] && [ -e "$FORCE_READER_PORT" ]; then
        log_msg "${GREEN}✓ Using forced Reader port: $FORCE_READER_PORT${NC}"
        reader_port="$FORCE_READER_PORT"
    else
        local reader_port=$(find_device_by_vid_pid 0x1d6b 0x4944)
        if [ -z "$reader_port" ]; then
            reader_port="$READER_DEFAULT"
            log_msg "${RED}Reader auto-detection failed; using default $reader_port${NC}"
        else
            log_msg "${GREEN}✓ Reader detected on $reader_port${NC}"
        fi
    fi
    
    if [ ! -e "$reader_port" ]; then
        log_msg "${RED}✗ Error: $reader_port does not exist${NC}"
        log_msg "Available USB devices:"
        ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || log_msg "No USB devices found"
        log_msg ""
        echo -n "Enter Reader port manually (default $READER_DEFAULT): "
        read -r reader_port
        reader_port=${reader_port:-$READER_DEFAULT}
    fi
    
    # Configure serial port for reader (9600 baud, 8N1)
    if command -v stty >/dev/null 2>&1; then
        stty -F "$reader_port" 9600 cs8 -cstopb -parenb 2>/dev/null || \
        stty -f "$reader_port" 9600 cs8 -cstopb -parenb 2>/dev/null || \
        log_msg "Warning: Could not configure serial port with stty"
        log_msg "Configured $reader_port to 9600 baud"
    else
        log_msg "Warning: stty not available, skipping port configuration"
    fi
    
    log_msg "${GREEN}✓ Reader port ready: $reader_port${NC}"
    echo "$reader_port"
    return 0
}

check_rfideas_device() {
    log_msg "Searching for RFIDEAs device (VID: 0x0c27)..."

    if [ -e "$RFIDEAS_EVENT" ]; then
        log_msg "${GREEN}✓ RFIDEAs event device detected at $RFIDEAS_EVENT${NC}"
        return 0
    fi

    for device in /sys/bus/usb/devices/*/idVendor; do
        local vid=$(cat "$device" 2>/dev/null)
        if [ "$vid" = "0c27" ]; then
            log_msg "${GREEN}✓ RFIDEAs USB device found (but event path not set)${NC}"
            return 0
        fi
    done

    log_msg "${RED}✗ RFIDEAs device not found${NC}"
    return 1
}

# Translate /dev/input/eventX key sequences to text characters
decode_rfideas_keys() {
    local input_data="$1"

    if [ -z "$input_data" ]; then
        echo ""
        return
    fi

    # Normalize case key names to simple output
    echo "$input_data" | awk 'BEGIN {shift=0;out=""}
    /EV_KEY/ {
      if ($3 != "DOWN") next
      if ($2 == "KEY_LEFTSHIFT" || $2 == "KEY_RIGHTSHIFT") { shift=1; next }
      if ($2 == "KEY_ENTER") { print out; exit }

      map["KEY_0"]="0"; map["KEY_1"]="1"; map["KEY_2"]="2"; map["KEY_3"]="3";
      map["KEY_4"]="4"; map["KEY_5"]="5"; map["KEY_6"]="6"; map["KEY_7"]="7";
      map["KEY_8"]="8"; map["KEY_9"]="9";
      map["KEY_A"]="a"; map["KEY_B"]="b"; map["KEY_C"]="c"; map["KEY_D"]="d";
      map["KEY_E"]="e"; map["KEY_F"]="f"; map["KEY_G"]="g"; map["KEY_H"]="h";
      map["KEY_I"]="i"; map["KEY_J"]="j"; map["KEY_K"]="k"; map["KEY_L"]="l";
      map["KEY_M"]="m"; map["KEY_N"]="n"; map["KEY_O"]="o"; map["KEY_P"]="p";
      map["KEY_Q"]="q"; map["KEY_R"]="r"; map["KEY_S"]="s"; map["KEY_T"]="t";
      map["KEY_U"]="u"; map["KEY_V"]="v"; map["KEY_W"]="w"; map["KEY_X"]="x";
      map["KEY_Y"]="y"; map["KEY_Z"]="z";

      if ($2 in map) {
        ch = map[$2]
        if (shift) {
          ch = toupper(ch)
          shift = 0
        }
        out = out ch
      }
    }
    END { if (out != "") print out }
    '
}

read_rfideas() {
    local timeout_sec=${1:-0.5}

    if [ ! -e "$RFIDEAS_EVENT" ]; then
        echo "NOT DETECTED"
        return 1
    fi

    if ! command -v getevent >/dev/null 2>&1; then
        echo "NOT DETECTED"
        return 1
    fi

    local raw=$(timeout "$timeout_sec" getevent -l "$RFIDEAS_EVENT" 2>/dev/null)
    if [ -z "$raw" ]; then
        echo "NOT DETECTED"
        return 1
    fi

    local decoded=$(decode_rfideas_keys "$raw")
    if [ -z "$decoded" ]; then
        echo "NOT DETECTED"
        return 1
    fi

    echo "$decoded"
    return 0
}

# --- CONVERSION FUNCTIONS ---

convert_24bit() {
    local value=$1
    local value_int=$((value & 0xFFFFFF))
    local high=$((($value_int >> 16) & 0xFF))
    local folded_high=$(((high & 0x80) | (high & 0x07)))
    local out=$((($value_int & 0x00FFFF) | (folded_high << 16)))
    
    if [ $((folded_high & 0x07)) -ge 4 ]; then
        out=$(((out - 0x01042E) & 0xFFFFFF))
    fi
    
    printf "%d" "$out"
}

int24_to_hex6() {
    local value=$1
    value=$((value & 0xFFFFFF))
    printf "%06X" "$value"
}

# --- SERIAL I/O FUNCTIONS ---

send_to_device() {
    local device=$1
    local data=$2
    
    if [ ! -w "$device" ]; then
        log_msg "${RED}Cannot write to $device${NC}"
        return 1
    fi
    
    # Try dd first (more reliable on Android)
    if command -v dd >/dev/null 2>&1; then
        printf "%s\r\n" "$data" | dd of="$device" 2>/dev/null
    else
        # Fallback to printf + cat
        printf "%s\r\n" "$data" > "$device" 2>/dev/null
    fi
    
    return 0
}

send_ctrl_c() {
    local device=$1
    
    if [ ! -w "$device" ]; then
        return 1
    fi
    
    # Send Ctrl+C (0x03)
    if command -v printf >/dev/null 2>&1; then
        printf '\003' | dd of="$device" 2>/dev/null
    fi
    
    return 0
}

read_from_device() {
    local device=$1
    local timeout_seconds=$2
    
    if [ ! -r "$device" ]; then
        echo "NOT DETECTED"
        return 1
    fi

    local data=""
    local attempt=0
    local max_attempts=3
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))

        # Prefer `timeout + dd` because it reads raw bytes and does not depend on line buffering.
        if command -v timeout >/dev/null 2>&1 && command -v dd >/dev/null 2>&1; then
            local tmpfile="/tmp/read_$$"
            timeout "$timeout_seconds" dd if="$device" bs=1 count=256 of="$tmpfile" 2>/dev/null
            if [ -f "$tmpfile" ] && [ -s "$tmpfile" ]; then
                data=$(tr -d '\0' < "$tmpfile" | xargs)
            fi
            rm -f "$tmpfile" 2>/dev/null

        elif command -v timeout >/dev/null 2>&1; then
            data=$(timeout "$timeout_seconds" cat "$device" 2>/dev/null | tr -d '\0' | xargs)
        
        elif command -v dd >/dev/null 2>&1; then
            local tmpfile="/tmp/read_$$"
            dd if="$device" bs=1 count=256 of="$tmpfile" 2>/dev/null &
            local dd_pid=$!
            sleep "$timeout_seconds"
            kill "$dd_pid" 2>/dev/null
            wait "$dd_pid" 2>/dev/null
            if [ -f "$tmpfile" ] && [ -s "$tmpfile" ]; then
                data=$(tr -d '\0' < "$tmpfile" | xargs)
            fi
            rm -f "$tmpfile" 2>/dev/null

        else
            data=""
        fi

        if [ -n "$data" ]; then
            echo "$data"
            return 0
        fi

        sleep 0.05
    done

    echo "NOT DETECTED"
    return 1
}

is_valid_reader_line() {
    local line="$1"
    if [ -z "$line" ] || [ "$line" = "NOT DETECTED" ]; then
        return 1
    fi

    if echo "$line" | grep -q '^helloID:invalid_req'; then
        return 1
    fi

    if echo "$line" | grep -q '^LF:'; then
        return 0
    fi

    if echo "$line" | grep -q '^helloID:'; then
        return 0
    fi

    return 1
}

find_valid_reader_line() {
    local raw="$1"
    local line

    while IFS= read -r line; do
        line=$(echo "$line" | tr -d '\r')
        [ -z "$line" ] && continue

        if echo "$line" | grep -q '^LF:'; then
            echo "$line"
            return 0
        fi

        if echo "$line" | grep -q '^helloID:invalid_req'; then
            continue
        fi

        if echo "$line" | grep -q '^helloID:'; then
            echo "$line"
            return 0
        fi
    done <<EOF
$raw
EOF

    return 1
}

# --- MAIN LOOP VARIABLES READY ---


# --- READER THREAD FUNCTION ---

reader_thread() {
    local reader_port=$1
    
    log_msg "Reader thread ready (would read from $reader_port)"
    
    # Keep thread alive
    while true; do
        sleep 1
    done
}

# --- MAIN LOOP ---

main() {
    log_msg "Starting RFID Card Emulator (Android Shell Version)"
    log_msg "Temp directory: $TEMP_DIR"
    
    # Ensure temp directory exists
    if [ ! -d "$TEMP_DIR" ]; then
        log_msg "Creating temp directory: $TEMP_DIR"
        mkdir -p "$TEMP_DIR" 2>/dev/null || TEMP_DIR="/tmp"
        log_msg "Using temp directory: $TEMP_DIR"
    fi
    
    # Get device ports
    log_msg "Detecting devices..."
    local flipper_port=$(check_flipper_device)
    local reader_port=$(check_reader_device)
    
    if [ -z "$flipper_port" ] || [ -z "$reader_port" ]; then
        log_msg "${RED}✗ Failed to get required device ports${NC}"
        exit 1
    fi
    
    # If they collide, try finding reader on a different port
    if [ "$flipper_port" = "$reader_port" ]; then
        log_msg "${RED}Warning: both devices mapped to $flipper_port, trying next candidate for reader${NC}"
        reader_port=$(find_device_by_vid_pid 0x1d6b 0x4944 "$flipper_port")
        if [ -n "$reader_port" ] && [ "$reader_port" != "$flipper_port" ]; then
            log_msg "${GREEN}✓ Reader re-mapped to $reader_port${NC}"
        else
            log_msg "${RED}✗ ERROR: Flipper and Reader still colliding after re-check${NC}"
            log_msg "Please ensure each hardware device is on separate tty devices and re-run."
            exit 1
        fi
    fi
    
    check_rfideas_device
    
    # Start reader thread in background (optional)
    log_msg "Starting reader thread..."
    reader_thread "$reader_port" &
    local reader_pid=$!
    
    # Create/clear log file with header
    {
        echo "Nr,Emulated UID,HelloID,Converted,RFIDEAs,Compare"
    } > "$LOG_FILE"
    log_msg "Created log file: $LOG_FILE"
    
    # Print headers to console
    echo ""
    echo "RFID Card Emulation Started"
    printf "%5s | %20s | %20s | %20s | %20s | %10s\n" "Nr" "Emulated UID" "HelloID" "Converted" "RFIDEAs" "Compare"
    echo "-----+-----------------------+-----------------------+-----------------------+-----------------------+----------"
    
    # Determine starting Nr from log file
    local start_nr=1
    if [ -f "$LOG_FILE" ]; then
        local last_nr=$(tail -1 "$LOG_FILE" 2>/dev/null | awk -F',' '{print $1}')
        if [ -n "$last_nr" ] && [ "$last_nr" -gt 0 ] 2>/dev/null; then
            start_nr=$((last_nr + 1))
            log_msg "Resuming from card $start_nr"
        fi
    fi
    
    # Main emulation loop - iterate through all cards
    local i=$start_nr
    local iterations=0
    local value=$START_VALUE
    local no_data_count=0
    while [ $iterations -lt $NUM_CARDS ] && [ $value -le $((0xFFFFFF)) ]; do
        # Reset at intervals
        if [ $iterations -gt 0 ] && [ $((iterations % RESET_INTERVAL)) -eq 0 ]; then
            log_msg "${GREEN}Resetting Flipper (iteration $iterations)${NC}"
            sleep 1
        fi
        
        # Generate UID for this iteration
        local euid=$(printf "00000012D6%06X" "$value")
        
        # Extract last 10 chars for emulation
        local key_suffix=${euid:6}  # All chars after "000000"
        
        # NOTE: Flipper emulation is disabled in this mode. You will emulate manually.
        log_msg "Flipper emulator command disabled; expecting manual card injection now"
        
        # Wait for reader input with timeout and filter invalid_req noise
        log_msg "Waiting for reader response (timeout: ${READER_TIMEOUT}s, retries: ${READER_RETRIES})..."
        local reader_raw="NOT DETECTED"
        for attempt in $(seq 1 "$READER_RETRIES"); do
            local tmp=$(read_from_device "$reader_port" "$READER_TIMEOUT")
            log_msg "Reader attempt $attempt raw: $tmp"
            if [ "$tmp" != "NOT DETECTED" ]; then
                local candidate=$(find_valid_reader_line "$tmp")
                if [ -n "$candidate" ]; then
                    reader_raw="$candidate"
                    break
                fi
            fi
            sleep 0.05
        done
        log_msg "Selected reader raw: $reader_raw"

        reader_read="NOT DETECTED"
        if [ "$reader_raw" != "NOT DETECTED" ]; then
            # Normalize and parse the line. LF:... should translate to UID.
            reader_raw=$(echo "$reader_raw" | tr -d '\r\n')
            if echo "$reader_raw" | grep -q '^LF:'; then
                #  LF:CASI-RUSCO:00000012D6050A0F
                local cleaned=$(echo "$reader_raw" | awk -F':' '{print $NF}')
            elif echo "$reader_raw" | grep -q '^helloID:'; then
                # Could be invalid_req or real ID
                local cleaned=$(echo "$reader_raw" | awk -F':' '{print $2}')
            else
                local cleaned="$reader_raw"
            fi

            cleaned=$(echo "$cleaned" | tr -cd '0-9A-Fa-f')
            if [ ${#cleaned} -ge 6 ]; then
                reader_read=$cleaned
            fi
        fi

        log_msg "Parsed reader value: $reader_read"

        # Debug: Log raw hex if not detected
        if [ "$reader_read" = "NOT DETECTED" ]; then
            log_msg "Reader returned no data - checking device..."
            no_data_count=$((no_data_count + 1))
        else
            no_data_count=0
        fi

        if [ "$no_data_count" -ge "$CONSECUTIVE_NODATA_LIMIT" ]; then
            log_msg "${RED}Warning: $no_data_count consecutive reads had no data, check wiring and trigger card now${NC}"
            sleep 1
            no_data_count=0
        fi
        
        sleep 0.2
        
        # Stop Flipper emulation (Ctrl+C) - skipped, manual operations only
        # send_ctrl_c "$flipper_port"
        # log_msg "Sent Ctrl+C to Flipper"
        
        # Convert the received UID
        local converted_uid="NOT DETECTED"

        # Read RFIDEAs keyboard output from event device (if available)
        local rfideas_read="$(read_rfideas 0.7)"
        if [ -z "$rfideas_read" ] || [ "$rfideas_read" = "NOT DETECTED" ]; then
            rfideas_read="NOT DETECTED"
        fi

        if [ "$reader_read" != "NOT DETECTED" ] && [ ${#reader_read} -ge 6 ]; then
            # Extract last 6 characters
            local last_chars=${reader_read#???????????????????}
            if [ ${#last_chars} -lt 6 ]; then
                last_chars=$(printf "%06s" "$last_chars" | sed 's/ /0/g')
            else
                last_chars=${last_chars: -6}
            fi
            
            # Convert from hex
            local int_value=$((16#$last_chars))
            local converted_int=$(convert_24bit "$int_value")
            local hex_value=$(int24_to_hex6 "$converted_int")
            
            # Keep first 10 chars and append converted value
            local prefix=${reader_read:0:10}
            converted_uid="$prefix$hex_value"
        fi
        
        # Format displays
        local emulated_display="$euid"
        local helloid_display="$reader_read"
        local converted_display="$converted_uid"
        local rfideas_display="NOT DETECTED"
        [ "$rfideas_read" != "NOT DETECTED" ] && rfideas_display="000000$rfideas_read"
        
        # Compare results
        local compare_result="ERROR"
        if [ "$converted_display" != "NOT DETECTED" ] && [ "$converted_display" != "ERROR" ] && \
           [ "$rfideas_display" != "NOT DETECTED" ]; then
            if [ "$converted_display" = "$rfideas_display" ]; then
                compare_result="Matched"
            else
                compare_result="Not Matched"
            fi
        fi
        
        # Log and print
        echo "$i,$emulated_display,$helloid_display,$converted_display,$rfideas_display,$compare_result" >> "$LOG_FILE"
        
        # Print progress (every 10 iterations to prevent spam)
        if [ $((iterations % 10)) -eq 0 ]; then
            printf "%5d | %-20s | %-20s | %-20s | %-20s | %10s\n" \
                "$i" "$emulated_display" "$helloid_display" "$converted_display" "$rfideas_display" "$compare_result"
        fi
        
        sleep "$DELAY_BETWEEN_CARDS"
        
        # Increment counters and value
        i=$((i + 1))
        iterations=$((iterations + 1))
        value=$((value + STEP_SIZE))
    done
    
    log_msg "Emulation loop completed. Processed $iterations cards."
    
    # Cleanup
    log_msg "Cleaning up..."
    kill $reader_pid 2>/dev/null
    
    log_msg "${GREEN}✓ All cards emulated and logged to: $LOG_FILE${NC}"
}

# --- MAIN EXECUTION ---

log_msg "================================"
log_msg "RFID Emulator Shell Script v1.0"
log_msg "================================"

if [ "$EUID" -ne 0 ] 2>/dev/null; then
    log_msg "${RED}Warning: This script should ideally be run as root for full device access${NC}"
fi

main "$@"
exit_code=$?
log_msg "Script exited with code: $exit_code"
exit $exit_code
