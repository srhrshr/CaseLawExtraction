# LegalTextExtraction

This is a program written in Python, that extracts information such as names of petitioners, respondents and the members of the coram, counsel, dates of pronouncing or reserving order or judgement from legal documents in PDF, using Python's ```re``` package for pattern matching and ```pdfminer``` for PDF parsing


### Installation
The program is tested on Python 2.7.6 and makes use of the external libraries which need to be installed.
```sh
$ pip install pdfminer
$ pip install python-dateutil
$ pip install inflect
```
The program is a single file named ```pdf_parser.py``` which can be run from CMD prompt:
```sh
$ python pdf_parser.py filename.pdf filename1.pdf ..
```
It generates one ```XMLOutput - filename.xml``` file corresponding to every input file.

 


