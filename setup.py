import setuptools

setuptools.setup(
    name="eolreportcertificate",
    version="1.0.0",
    author="Oficina EOL UChile",
    author_email="eol-ing@uchile.cl",
    description="Allows you to download a csv of Certificates Issued",
    url="https://eol.uchile.cl",
    packages=setuptools.find_packages(),
    install_requires=[
        "unidecode>=1.1.1"
        ],
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "lms.djangoapp": ["eolreportcertificate = eolreportcertificate.apps:EolReportCertificateConfig"]},
)
