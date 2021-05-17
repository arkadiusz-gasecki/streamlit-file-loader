import streamlit as st
import pandas as pd
import io, base64
#import chardet
import SessionState

from matplotlib import pyplot as plt

from pandas_profiling import ProfileReport
from streamlit_pandas_profiling import st_profile_report


### ------- rule section --------- ###

### function that reads Excel file with rules
#!! (it could be replaced by ectract from database if app had such connection)
### function expectes minimum 1 sheet
### each sheet has to contain following columns, with description of metadata
##  - Target Column   : name of column in table in database, case insensitive
##  - Attribute Name  : name of column in file being uploaded, case insensitive
##  - Data Type       : type of column in file being uploaded case insensititve, allowed: 'boolean','byte','integer','smallint','floating point','date time','time','unicode string','object','string'
##  - Column Size     : maximum length of column allowed, number only, applicable only to 'string' and 'object' types
def get_rule(file,sheet_name):
	extension = file.name.split('.')[-1]

	#take only files with acceptable extensions
	if extension.upper() in ['XLS', 'XLSX']:
		xls = pd.ExcelFile(file)
		try:
			# take first sheet if it was not defined
			if sheet_name is None: sheet_name = xls.sheet_names[0]
			
			df = pd.read_excel(file, engine='openpyxl',sheet_name=sheet_name)
			for exp_col in ['Target Column', 'Attribute Name', 'Data Type', 'Column Size']:
				if exp_col not in df.columns.tolist():
					st.write("Missing expected column %s in configuration sheet %s" % (exp_col, sheet_name))
					return (None, None)
		except:
			st.write("Expected sheet %s not found" % sheet_name)
			return (None, None)

	return (df, xls.sheet_names)


### function renders part reponsible for upload of XLS file with rules
def rule_uploader_section(file_type):
	st.markdown('### Rules file')
	rule = st.file_uploader("Upload excel file with rules", type=['xls','xlsx'], key='2')

	if not rule:
		st.write("Upload a .csv or .xlsx file with rules definition")
		return (None, None)
	else:
		return get_rule(rule,file_type)


### ------- file upload section --------- ###


### function that reads CSV or Excel file that is intended to be uploaded
### uses parameters selected in sidebar
@st.cache(persist=True)
def get_df(file, file_encoding, file_separator, file_quoting):
	extension = file.name.split('.')[-1]
	quote = None
	if file_quoting == 'Sinqle quotes':
		quote = "'"
	elif file_quoting == 'Double quotes':
		quote = '"'

	if file.type == 'text/csv' or extension.upper() == 'CSV':
		if quote is None:
			df = pd.read_csv(file,sep=file_separator,encoding=file_encoding)
		else:
			df = pd.read_csv(file,sep=file_separator,encoding=file_encoding,quotechar=quote)
	elif extension.upper() == 'XLSX':
		df = pd.read_excel(file, engine='openpyxl')

	df.columns = map(str.upper, df.columns)
	df.index += 1
	
	return df


### function renders part reponsible for upload of target CSV or XLS file
def file_uploader_section(filename, file_encoding, file_separator, file_quoting):

	st.markdown('------------------------------------------------------------------')
	st.markdown('#### '+filename+' file')
	st.markdown('------------------------------------------------------------------')
	file = st.file_uploader("Upload %s file" % filename, type=['csv','xlsx'], key='1')
	
	if not file:
		st.write("Upload a .csv file to get started")
		return None
	else:
		#print(chardet.detect(file))
		df = get_df(file, file_encoding, file_separator, file_quoting)
		if st.checkbox("Show raw data", False):
			if len(df) > 10000:
				st.markdown('_File too big. First 10000 rows presented._')
				st.write(df.head(10000))
			else:
				st.write(df)
		return df


### ------- help functions section --------- ###

def get_report(df):
	pr = ProfileReport(df, explorative=True)
	return pr

###function generate insert that could be submitted if app had connection to database
def show_insert(report_dict, table):

	insert_cols = list()
	select_cols = list()
	#take length of first list
	length = len(report_dict['Expected column'])
	#go through all lists using index from length
	for i in range(length):
		if report_dict['Status'][i] == 'OK':
			insert_cols.append(report_dict['Expected column'][i])
			select_cols.append(report_dict['Actual column'][i])
	
	query =( 'DELETE FROM %s;\nINSERT INTO %s \n(\n  %s\n) \n SELECT \n  %s \nFROM dataframe;' % (table, table, '\n, '.join(insert_cols), '\n, '.join(select_cols)))
	return query

### generator of content
def main():
	### --- generate header of website --- ###
	st.title('Upload files')
	st.write('Select, verify and load data from selected CSV or XLS files into database, based upon delivered rules')

	### --- define session state values --- ###
	session_state = SessionState.get(sheet_names=None, sheet_selected=None)

	### --- generate sidebar --- ###
	#!! make first selector dependant on sheets in excel with rules
	if session_state.sheet_names is None or session_state.sheet_names == list():
		file_type = st.sidebar.empty()
	else:
		file_type = st.sidebar.selectbox('Select file type', ('') if session_state.sheet_names is None else session_state.sheet_names)
		session_state.sheet_selected = file_type
	file_encoding = st.sidebar.selectbox('Select file encoding', ('iso-8859-1', 'utf-8'))
	file_separator = st.sidebar.selectbox('Select file separator', (';',',','|'))
	file_quoting = st.sidebar.selectbox('Select file quotation', ('No quotes', 'Single quotes', 'Double quotes'))
	load_type = st.sidebar.radio('Select mode', ('Upload to DB', 'File analyzer'))

	### --- load excel file with rules --- ###
	### --- with first upload, take first sheet as default one --- ###
	(dr, sheet_names) = rule_uploader_section(session_state.sheet_selected)
	session_state.sheet_names = sheet_names
	if session_state.sheet_selected is None and session_state.sheet_names is not None:
		session_state.sheet_selected = session_state.sheet_names[0]

	### --- if selector for file type is empty, set it with sheets from excel --- ###
	if dr is not None and not isinstance(file_type,str):
		file_type.selectbox('Select file type', session_state.sheet_names)
		
	### --- give possibility to show raw data --- ###
	if st.checkbox('Show raw data', False, key='3'):
		st.write(dr)


	### --- load actual file --- ###
	df = None
	if session_state.sheet_selected is not None:
		df = file_uploader_section(session_state.sheet_selected, file_encoding, file_separator, file_quoting)

	### --- display report from File analyzer, if requested --- ###
	if df is not None and load_type == 'File analyzer':
		if st.checkbox('This is time consuming operation (non-cacheable), tick if you want to continue', False, key='5'):
			st_profile_report(get_report(df))
		return None


	### --- now, run parsing if both data file and rule file are uploaded --- ###
	if df is not None and dr is not None:
		# fixed dictionary that will be used to verify if types are ok
		types_conv = { '-': None
			,'boolean': '?'
			,'byte': 'b'
			,'integer': 'i'
			,'smallint': 'i'
			,'floating point': 'f'
			,'date time': 'M'
			,'time': 'm'
			,'unicode string': 'U'
			,'object': 'O'
			,'string': 'O'
			}

		# transformation of columns to eliminate issues based on case sensitivity
		expected_columns = dr['Attribute Name'].str.upper().tolist()
		cols = df.columns.str.upper().tolist()

		# take type of each column
		df_types = pd.DataFrame(df.dtypes, columns=['Data Type'])

		# gather result of parsing in dictionary, so it can be displayed as table afterwards
		report_dict = {
			'Expected column': list(),
			'Expected type': list(),
			'Actual column': list(),
			'Actual type': list(),
			'Status': list()
		}

		# flag to determine at the end whether file passed all tests
		file_is_ok = True

		for col in cols:
			# make verification for columns that are expected
			if col in expected_columns:
				expected_type = dr[dr['Attribute Name'].str.upper()==col.upper()]['Data Type'].values[0].lower()
				actual_type = df_types.loc[col]['Data Type']

				report_dict['Expected column'].append(col)
				report_dict['Actual column'].append(col)

				report_dict['Expected type'].append(expected_type)
				report_dict['Actual type'].append(actual_type)
				
				### check if type is ok
				try:
					test_df = df.copy()
					series = test_df[col].fillna(0).astype(types_conv[expected_type])
					report_dict['Status'].append('OK')
				except:
					report_dict['Status'].append('Incompatible Types')
					file_is_ok = False

				### check if length is ok (apply only if type was ok)
				if actual_type == 'object' and file_is_ok:
					expected_length = dr[dr['Attribute Name'].str.upper()==col.upper()]['Column Size'].values[0]
					actual_length = df[col].str.len().max()
					if actual_length > expected_length:
						err = df[df[col].str.len() > expected_length].head(1)
						report_dict['Status'][-1] = 'Column too long, expected:%i, but found: %i in row %i' % (expected_length, actual_length, err.index.values[0])
						file_is_ok = False

			# prepare list for unexpected columns
			elif col not in expected_columns:
				actual_type = df_types.loc[col]['Data Type']

				report_dict['Expected column'].append('...')
				report_dict['Actual column'].append(col)

				report_dict['Expected type'].append('...')
				report_dict['Actual type'].append(actual_type)
				report_dict['Status'].append('Unexpected column')
				file_is_ok = False

		# prepared list for columns that are expected but missing
		for col in expected_columns:
			if col not in cols:
				expected_type = dr[dr['Attribute Name'].str.upper()==col.upper()]['Data Type'].values[0]

				report_dict['Expected column'].append(col)
				report_dict['Actual column'].append('')

				report_dict['Expected type'].append(expected_type)
				report_dict['Actual type'].append('')
				report_dict['Status'].append('Expected column missing')
				file_is_ok = False

		# generate summary of checking report
		st.markdown('------------------------------------------------------------------')
		st.markdown('### File check report ### ')
		report_df = pd.DataFrame(report_dict)
		report_df.index += 1
		
		st.table(report_df)

		st.markdown('------------------------------------------------------------------')
		st.markdown('### Saving file to database ### ')

		if file_is_ok:
			save_db = st.button('Save file to DB')
		else:
			st.markdown("File does not match the rules uploaded. In order to fix it, execute one of the following actions:")
			st.markdown("* Adjust the rules file")
			st.markdown("* Correct file with data")
			st.markdown("Alternatively, you can save only data for the proper columns")
			save_db = st.button('Save only matching columns',help='Only these columns will be saved for which status is OK')
			
		if save_db:
			st.code(show_insert(report_dict, file_type), language='sql')

main()
