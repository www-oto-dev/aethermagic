
export PIP_REQUIRE_VIRTUALENV="false"
pip3 install build twine hatchling
python3 -m build --no-isolation
twine check dist/*
twine upload dist/*