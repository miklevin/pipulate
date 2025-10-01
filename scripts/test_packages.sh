#!/usr/bin/env bash

# This script tests each package in a requirements.txt file to see if
# its own build process fails in the read-only Nix store environment.

REQS_FILE="requirements.txt"
GOOD_PACKAGES="good_packages.txt"
BAD_PACKAGES="bad_packages.txt"
LOG_FILE="test_packages.log"

# --- Pre-flight Checks ---
# Ensure we are inside a Nix shell
if [ -z "$IN_NIX_SHELL" ]; then
    echo "❌ Error: This script must be run inside a 'nix develop' shell."
    exit 1
fi

# Ensure the virtual environment exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "❌ Error: Virtual environment not found at '.venv/bin/activate'."
    echo "Please run 'rm -rf .venv' and then 'nix develop .#quiet' to create it."
    exit 1
fi

# Ensure requirements.txt exists
if [ ! -f "$REQS_FILE" ]; then
  echo "❌ Error: '$REQS_FILE' not found!"
  exit 1
fi

# --- Setup ---
echo "🧹 Clearing previous results and logs..."
rm -f "$GOOD_PACKAGES" "$BAD_PACKAGES" "$LOG_FILE"
touch "$GOOD_PACKAGES" "$BAD_PACKAGES"

source .venv/bin/activate
echo "✅ Virtual environment activated."

PACKAGE_COUNT=$(grep -vcE '^\s*(#|$)' "$REQS_FILE")
CURRENT_PKG=0

echo "▶️ Starting test of $PACKAGE_COUNT packages..."

# --- Main Test Loop ---
while IFS= read -r package || [[ -n "$package" ]]; do
  # Skip empty lines or comments
  if [[ -z "$package" ]] || [[ "$package" == \#* ]]; then
    continue
  fi

  ((CURRENT_PKG++))
  echo -n "[$CURRENT_PKG/$PACKAGE_COUNT] Testing '$package'... "

  # Attempt to install the single package WITHOUT its dependencies.
  output=$(pip install --no-deps "$package" 2>&1)
  exit_code=$?

  if [ $exit_code -ne 0 ] && [[ "$output" == *"Read-only file system"* ]]; then
    echo "❌ Bad"
    echo "$package" >> "$BAD_PACKAGES"
  else
    echo "✅ Good"
    echo "$package" >> "$GOOD_PACKAGES"
  fi
  # Append all output to the log file for later review.
  echo -e "\n--- Log for $package ---\n$output\n--- End Log ---\n" >> "$LOG_FILE"

done < "$REQS_FILE"

echo "🎉 Testing complete!"
echo "See '$GOOD_PACKAGES' for packages that installed correctly."
echo "See '$BAD_PACKAGES' for packages with faulty setups."