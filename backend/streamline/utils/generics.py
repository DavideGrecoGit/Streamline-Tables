import os
import re
import pandas as pd
import mimetypes
from zipfile import ZipFile
from django.http import HttpResponse, HttpResponseNotFound
from django.conf import settings
from streamline.models import Table_PDF, Table_HTML

def get_options(options):
    '''
    Receives a string of 1's and 0's corresponding to different user settings
    ''' 
    return [int(char) if char.isdigit() else 1 for char in options] if options else []


def create_zip(paths, folder=settings.CSV_DIR, zipPath="tables.zip"):
    '''
    Will create and return the path to a zip file of all csv files in folder
    ''' 
    os.chdir(folder)
    with ZipFile(zipPath, 'w') as zipFile:
        for path in paths:
            zipFile.write(os.path.basename(path))
    
    return os.path.abspath(zipPath)


def check_valid_page_input(pages):
    '''
    Ensures the input follows a valid format
    '''
    regex = "^all$|^\s*[0-9]+\s*((\,|\-)\s*[0-9]+)*\s*$"
    return re.search(pages, regex)


def extract_doi(text):
    '''
    Should extract the doi if it is present from either a url, or html body
    Regex found at: https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    https://stackoverflow.com/questions/27910/finding-a-doi-in-a-document-or-page
    '''
    doi_regex = "\b(10[.][0-9]{4,}(?:[.][0-9]+)*/\S+)"

    if (groups := re.search(doi_regex, text)):
        doi = groups.group(1)
    else:
        doi = ""

    print(f"doi = {doi}")
    return doi.replace("/","_")


def get_filepaths_from_id(table_ids, table_type):
    '''
    Takes a list of table_ids and returns a list of each tables corresponding csv path
    '''
    table_paths = []
    table_model = Table_PDF if table_type == "pdf" else Table_HTML
    
    for table_id in table_ids.split(","):
        
        if (table_obj := table_model.objects.filter(id = int(table_id)).first()):
            table_paths.append(table_obj.file_path)
    
    return table_paths


def get_as_html(table):
    '''
    Returns a html representation of a table, or an error message if table couldn't be read
    '''
    try:
        print("\nfilepath: ",table.file_path)
        
        if table.file_path.endswith(".csv"):
            df_xls = pd.read_csv(table.file_path, index_col=False, skip_blank_lines=True)
        else:
            df_xls = pd.read_excel(table.file_path, index_col=False)
      
        df_xls.dropna(how="all", inplace=True)
        df_xls.fillna('', inplace=True)

        df_xls.set_index(df_xls.columns[0], inplace=True)
        
        df_xls.columns = [ "" if "Unnamed:" in c else c for c in df_xls.columns ]

        csv_html = df_xls.to_html(classes="table table-sm table-hover table-responsive", border=0)

    except:
        csv_html = "<p>Preview not available</p>"

    return csv_html


def create_context(url_obj, tables_obj, table_type="pdf"):
    '''
    Creates and returns a dictionary providing context to the webpage
    '''
    table_ids = ",".join([str(table.id) for table in tables_obj])
    tables_html = [( str(table.id), get_as_html(table) ) for table in tables_obj]

    context_dict = { "url_id": url_obj.id,
                     "table_count": len(tables_obj),
                     "table_type": table_type,
                     "Web_Page_Tables": tables_html,
                     "table_ids": table_ids }

    return context_dict


def create_file_response(file_path):
    '''
    Creates a HttpResponse with a file attatched, and returns the response
    '''
    print(f"--- Sending file {file_path} as HttpResponse")

    # guess_type() returns a tuple (type, encoding) we disregard the encoding
    mime_type, _ = mimetypes.guess_type(file_path)
    fname = os.path.basename(file_path)

    if not os.path.isfile(file_path):
        print("--- File(s) cannot be downloaded")
        return HttpResponseNotFound("<h1>File(s) cannot be downloaded</h1>")

    with open(file_path, 'rb') as file:
        response = HttpResponse(file, content_type=mime_type)
        response['Content-Disposition'] = f'attachment; filename={fname}'
        return response

    
