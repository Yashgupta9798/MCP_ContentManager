IMPORTANT - DO NOT USE THIS AS IT IS.

EXAMPLE 1
THIS IS FOR SEARCH
Query: Find record numbered 26/1
Intent: SEARCH
Action Plan:
{
  "path":"Record",
  "method":"GET",
  "parameters":{
    "number": "26/1",
    "format":"json",
    "properties":"NameString"
  },
  "operation":"SEARCH"
}

EXAMPLE 2
THIS IS FOR SEARCH
Query: Find all records created on 19th January, 2026
Intent: SEARCH
Action Plan:
{
  "path":"Record",
  "method":"GET",
  "parameters":{
    "createdon": "01/19/2026",
    "format":"json",
    "properties":"NameString"
  },
  "operation":"SEARCH"
}

EXAMPLE 3
THIS IS FOR CREATE
Query: Make a new document with name "My_doc".
Intent: CREATE
Action Plan:
{
  "path":"Record/",
  "method":"POST",
  "parameters":{
    "RecordRecordType":"document",
    "RecordTitle":"My_doc"
  },
  "operation":"CREATE"
}

EXAMPLE 4
THIS IS FOR UPDATE
Query: Update the record numbered 26/1, to title "updated_title"

{
  "path":"Record/",
  "method":"POST",
  "parameters_to_search":{
    // include only the keys the user supplied
    "number":"26/1"
  },
  "parameters_to_update":{
    // include only the keys the user supplied
    "RecordTitle":"updated_title"
  },
  "operation":"UPDATE"
}


DO NOT USE THIS AS IT IS.