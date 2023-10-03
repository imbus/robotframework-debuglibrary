check-manifest --update
rm -f dist/*.*
python setup.py bdist_wheel sdist
twine check dist/*
python setup.py check -r -s
twine upload dist/*