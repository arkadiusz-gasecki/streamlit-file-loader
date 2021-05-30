# streamlit-file-loader
Simple application based on streamlit that is intended to verify CSV or XLS files based on set of rules uploaded.

## Part 1 - definition of rules
At first we need excel files that will describe dataset that needs to be imported
Each sheet provides information about single expected dataset.
Following columns are expected:
  - Target Column   : name of column in table in database, case insensitive
  - Attribute Name  : name of column in file being uploaded, case insensitive
  - Data Type       : type of column in file being uploaded case insensititve, allowed: 'integer','float','string'
  - Column Size     : maximum length of column allowed, number only, applicable only to 'string' type


## Part 2 - loading of actual file
CSV or Excel file is expected in second part.
If it is CSV file, details about file structure (encoding, separator, quoting) are taken from sidebar fields

Based on rules taken from previous step, report is displayed, showing for each column:
- if it is expected
- if expected type is proper
- if expected length is proper (for object columns)
- actual name and type of column
At the end missing expected columns are displayed

## Part 3 - export
There are two options in last part:
- file can be exported to CSV. Settings from sidebar are used. Only valid columns are exported
- file can be saved to DB. As no connection is defined, this option shows only query that could be applied on database. Only valid columns would be uploaded
