# -*- coding: utf-8 -*-
import ast
import re

from setuptools import find_namespace_packages, setup

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("erpnext_ec/__init__.py", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

setup(
    name="erpnext_ec",
    version=version,
    description="ERPNext Ecuador - Localización ecuatoriana SRI",
    author="Raúl Santamaría",
    author_email="raulsantamariaobando@gmail.com",
    packages=find_namespace_packages(include=["erpnext_ec*"]),
    zip_safe=False,
    include_package_data=True,
    package_data={
        "erpnext_ec": [
            "**/*.json", "**/*.html", "**/*.js", "**/*.css", "**/*.xml", "**/*.xsd",
            "**/*.csv", "**/*.txt", "**/*.woff2", "**/*.png", "**/*.svg", "**/*.map",
            "**/*.min.js",
        ],
    },
)
