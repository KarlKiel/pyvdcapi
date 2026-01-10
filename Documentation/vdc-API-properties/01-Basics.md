# 1 Basics

- This document is based on the "vDC API" specification. Please refer to the corresponding document for general description of the API and the available messages/calls.
- This document specifies the named properties available for different types of addressable entities (vDC, vdSD, vDC host) as well as the properties common for all types of addressable entities.
- All strings are UTF-8 encoded
- Properties marked optional may or may not be available in a particular implementation. If not available, getProperty will just not return them in the result tree, but will NOT return an error response (see description of getProperty in the "vDC API" specification for details). However, a setProperty call containing a value for a non-implemented property will return an error.
