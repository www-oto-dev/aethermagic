#!/bin/bash

set -e  # Exit immediately on error


PROJECT_FILE="pyproject.toml"


# venv excluding
echo "➖ Removing venv"
if type deactivate &> /dev/null; then
  deactivate
fi
rm -fR ./venv
export PIP_REQUIRE_VIRTUALENV="false"

# Installing globaly
echo "🛠 Installing Tools"
pip3 install build twine hatchling




# Updating version
# - getting current version
current_version=$(grep -E '^version *= *"' "$PROJECT_FILE" | sed -E 's/.*"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/')
IFS='.' read -r major minor patch <<< "$current_version"

# - version +1
patch=$((patch + 1))
new_version="${major}.${minor}.${patch}"

echo "🔄 Updating version: $current_version → $new_version"
sed -i.bak -E "s/(version *= *\")${current_version}(\".*)/\1${new_version}\2/" "$PROJECT_FILE"
rm "${PROJECT_FILE}.bak"
grep version "$PROJECT_FILE"




# Building
echo "🧹 Removing previous dist files ..."
rm -f dist/*

echo "📦 Building package..."
python3 -m build --no-isolation


# Checking
echo "🔍 Checking distribution files..."
twine check dist/*

if [ $? -ne 0 ]; then
    echo "❌ Twine check failed. Upload canceled."
    exit 1
fi

# Uploading
echo "🚀 Uploading to PyPI..."
twine upload dist/*
echo "✅ Done."