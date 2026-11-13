#!/bin/sh
# Build a qflow bindir whose yosys is Yosys 0.70 (the system 0.52 segfaults
# on the TR10 Liberty) and whose vlogFanout is the no-resize wrapper.
set -e
dst=${1:-/tmp/opencode/qflow_bin}
mkdir -p "$dst"
for f in /usr/local/share/qflow/bin/*; do ln -sf "$f" "$dst/"; done
rm -f "$dst/yosys" "$dst/vlogFanout"
ln -sf "${YOSYS70:-/nix/store/cfry5mn7l5qk6cy730gspaa51fahc108-yosys-0.70/bin/yosys}" "$dst/yosys"
cp "$(dirname "$0")/vlogFanout" "$dst/vlogFanout"
chmod +x "$dst/vlogFanout"
echo "$dst"
