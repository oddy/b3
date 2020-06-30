
# B3 Design & Wire Format

This document describes the B3 binary format, including data type formats, the structure of composite items, and the format of the item header. It also documents semantics and policies for the two main types of packer - schema and schemaless.


## Core drivers and policy goals
These are in rough order of priority. 
* Simplicity 
* Correctness & Interoperability
* Flexibility
* Compactness
* Performance

## Format overview
B3 is primarily a TLV ("type-length-value") based format. Simple and complex data structures are all expressed on the wire as a consecutive series of **items**. Each Item has a data type, size, value, and optional key. 

B3 is a 'bottom up' format, where all items have a known size. This means B3:
* does not support support "unknown size" items, [^1] 
* does support nested items, however the 'inner' items must be packed first, before being included in outer items. 

[^1]: The only use-cases we could think of for unknown-size items were 1) huge data structures like DB tables which will have their own sizing anyway, and 2) streaming TCP scenarios which always end up being chunked anyway for a better UX.

## item format

An item consists of the item header, followed by the item value's data bytes. 


## how to do composite items

## data types 

## Schema pack/unpack semantics

## Schemaless pack/unpack semantics. 

## Forward & Backward compatibility



# Things we need to talk about
* null values
* compact zero values
* 


