import re
from django.http import HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import render
from streamline.models import Url_PDF, Url_HTML, Table_PDF, Table_HTML
from django.conf import settings

from .utils import html_to_csv, pdf_to_csv, generics

# Path to which resulting csv files will be saved (will be .../cs20-main/backend/saved)
CSV_PATH = settings.CSV_DIR
PDF_PATH = settings.PDF_DIR


def get_tables_from_html(request):
    '''
    Extracts table data from HTML
    '''
    # Get url and options
    url = request.GET.get('url', None)
    options = request.GET.get('options', None)

    if not url:
        print("\n--- No URL found")
        return HttpResponseBadRequest("<h1>Invalid Request</h1>")

    print('url:', url)
    print('options', options)

    # Set up options list 
    options_list = generics.get_options(options)

    html_obj = Url_HTML.objects.filter(url=url).first()
        
    if not html_obj:
        #store URL
        html_obj = Url_HTML.objects.create(url=url)
        print("--- New HTML URL ---", html_obj.url)

        #process page
        html_to_csv.extract(url, html_obj, save_path=CSV_PATH)
    
    # Query extracted tables
    tables_obj = Table_HTML.objects.filter(html_id=html_obj.id)
    
    if tables_obj:
        context_dict = generics.create_context(html_obj, tables_obj, table_type="html")
        return render(request, 'streamline/preview_page.html', context=context_dict)
    
    else:
        return render(request, 'streamline/no_tables.html', context={})


def get_tables_from_pdf(request):
    '''
    Extracts table data from PDF
    '''
    url = request.GET.get('url', None)
    pages = request.GET.get('pages', None)
    options = request.GET.get('options', None)

    if not pages or not url:
        print("\n--- No URL/Pages found")
        return HttpResponseBadRequest("<h1>Invalid Request</h1>")

    print('\nurl:', url)
    print('pages:', pages)
    print('options', options)

    #options - contains string of 01s to indicate true/falses 
    options_list = generics.get_options(options)

    tables_obj = []

    # Check if page input is valid
    if generics.check_valid_page_input(pages):

        print("\n--- Valid input")

        pdf_obj = Url_PDF.objects.filter(url=url).first()
        
        page_list = pdf_to_csv.pages_to_int(pages)

        # If the pdf already exists in db
        if pdf_obj:
            print("--- PDF Found ---", pdf_obj.url)

            pdf_path = pdf_obj.pdf_path

            pages, tables_obj = pdf_to_csv.get_missing_pages(page_list, pdf_obj.id, tables_obj)
            
        else:
            print("--- New PDF ---", url)
            # downloads pdf from right click
            pdf_path = pdf_to_csv.download_pdf(url, save_path=PDF_PATH)
            # store URL
            pdf_obj = Url_PDF.objects.create(url=url, pdf_path=pdf_path)

        #convert its table(s) into csv(s) and get table count
        if pages != "":
            new_tables = pdf_to_csv.download_pdf_tables(pdf_path, pdf_obj, save_path=CSV_PATH, pages=pages)
            tables_obj = tables_obj + new_tables
    
    else:
        print("\n--- Invalid input")
        return HttpResponseBadRequest("<h1>Invalid Input</h1>")

    if len(tables_obj) > 0:
        context_dict = generics.create_context(pdf_obj, tables_obj, table_type="pdf")
        return render(request, 'streamline/preview_page.html', context=context_dict)

    else:
        return render(request, 'streamline/no_tables.html', context={})


def download_file(request, table_ids, table_type):
    """
    A view to download either a zip of all tables, or a singular table
    table_id of 0 indicates the user wants all tables
    """

    if table_ids == None or table_type == None:
        print("\n--- Invalid Download request")
        return HttpResponseBadRequest("<h1>Invalid Request</h1>")

    table_paths = generics.get_filepaths_from_id(table_ids, table_type)

    # Only one file is selected

    if len(table_paths) == 0:
        print("\n--- File(s) not found")
        return HttpResponseNotFound("<h1>File(s) not found</h1>")

    if len(table_paths) == 1:
        file_path = table_paths[0]
    else:
        file_path = generics.create_zip(table_paths, folder=CSV_PATH)

    return generics.create_file_response(file_path)
