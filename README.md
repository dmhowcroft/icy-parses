README for icy-parses (formerly, icToolDist)
============================================

This package provides support for extracting integration cost from the
output of the Stanford Dependency Parser.

Usage
-----

Usage for plain SENTS files:

    ./integration_cost.py SENTS_FILE OUTPUT_FILE --stories

where a `SENTS_FILE` is a standard one-sentence-per-line corpus file.
It may or may not be tokenized already.
This script assumes they are not tokenized.

For plain SENTS files and sentence-level summary output:

    ./integration_cost.py SENTS_FILE OUTPUT_FILE --sentfeats

Inventory
---------

* `Stanford-Parser/`  
  contains the Stanford Parser instance, downloaded from the official
  page
* `Tests-StanParser/`  
  contains some test files, its purpose is to check the output of the
  stanford parser for special sentences

* `integration_cost.py`  
  main script for running `icy-parses`
* `InvokeStanfordParser.java`
  interface with the stanford-parser, to be later used with popen
  provided by Asad Sayeed
* `InvokeStanfordParser.class`  
  class file of the previous file  
  this is called by the Python scripts
* `README.md`  
  this file
  
Metadata
--------

Created by Asad Sayeed and/or Jesus Calvillo prior to 2015.  
Last modified by David M. Howcroft, April 2017.
