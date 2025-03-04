# wellpermitimporter

Well Permit GIS Importer
Hey there! This is a Python script I threw together to grab well permit forms (PDFs) from SharePoint, pull out the key details, stash them in a SQL Server database, and then shove them into ArcGIS Online as points on a map. It’s pretty handy if you’re dealing with stuff like IDWR well permits and want to cut down on manual GIS work. I’m no pro, but it works for me—hope it does for you too!
What It Does
Connects to SharePoint, downloads a well permit PDF.

Reads the PDF and grabs stuff like owner name, coordinates, and well purpose.

Sticks the data into a SQL Server table.

Pulls that data out and adds it as points to an ArcGIS Online layer.

What You’ll Need
Python 3 (I used 3.9, but 3.7+ should be fine).

Some Python libraries (see below).

A SharePoint site with a library (like "Well Permits") where PDFs live.

A SQL Server database with a table set up (I’ll show you the table).

An ArcGIS Online account with a feature layer to dump stuff into.

Credentials for all the above (SharePoint, SQL, ArcGIS).

Example Form:

<img width="815" alt="Screenshot 2025-03-03 at 6 12 03 PM" src="https://github.com/user-attachments/assets/03fde0d3-4d77-42dc-ab2d-883341c33174" />



Setup
Install the goodies:
Open your terminal and run:

pip install pdfplumber pandas pyodbc office365-rest-python-client arcgis

That’s it—those handle PDFs, data, SQL, SharePoint, and ArcGIS.

SQL Server Table:
Fire up SQL Server Management Studio (or whatever you use) and run this to make a table:
sql

CREATE TABLE WellPermits (
    PermitID INT IDENTITY(1,1) PRIMARY KEY,
    Owner NVARCHAR(100),
    Township NVARCHAR(10),
    Range NVARCHAR(10),
    Section INT,
    Quarter NVARCHAR(20),
    Latitude FLOAT,
    Longitude FLOAT,
    Purpose NVARCHAR(50),
    Depth INT,
    Flow INT,
    ProcessedDate DATETIME DEFAULT GETDATE(),
    GISImported BIT DEFAULT 0
);

This is where the well data hangs out.

Tweak the Script:
Grab the script below and update these bits with your own info:
site_url, username, password (SharePoint).

conn_str (SQL Server connection).

gis_url, layer_item_id, your_username, your_password (ArcGIS Online).

file_name (the PDF name in SharePoint).

The Code
Save this as well_importer.py or whatever you like:
python

import pdfplumber
import pandas as pd
import pyodbc
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
import re

# Pull a PDF from SharePoint
def get_pdf_from_sharepoint(site_url, username, password, library_name, file_name):
    ctx = ClientContext(site_url).with_credentials(UserCredential(username, password))
    library = ctx.web.lists.get_by_title(library_name)
    file = library.get_items().filter(f"FileLeafRef eq '{file_name}'").get().execute_query()[0]
    file_url = file.properties["FileRef"]
    downloaded_file = ctx.web.get_file_by_server_relative_url(file_url).download().execute_query()
    return downloaded_file.local_path

# Extract data from the PDF
def extract_form_data(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()
        patterns = {
            "Owner": r"Well Owner Name: (.+)",
            "Township": r"Township: (\d+[NS])",
            "Range": r"Range: (\d+[EW])",
            "Section": r"Section: (\d+)",
            "Quarter": r"Quarter-Quarter: (.+)",
            "Latitude": r"Latitude: (\d+° \d+' \d+\" [NS])",
            "Longitude": r"Longitude: (\d+° \d+' \d+\" [EW])",
            "Purpose": r"Purpose of Use: \[X\] (\w+)",
            "Depth": r"Proposed Depth: (\d+) feet",
            "Flow": r"Estimated Flow Rate: (\d+) gpm"
        }
        data = {key: re.search(pattern, text).group(1) if re.search(pattern, text) else None 
                for key, pattern in patterns.items()}
        
        def dms_to_dd(dms_str):
            if not dms_str:
                return None
            d, m, s = re.findall(r"(\d+)", dms_str)
            direction = dms_str[-1]
            dd = float(d) + float(m)/60 + float(s)/3600
            return dd if direction in ["N", "E"] else -dd
        
        data["Latitude"] = dms_to_dd(data["Latitude"])
        data["Longitude"] = dms_to_dd(data["Longitude"])
        return data

# Stick it in SQL Server
def store_in_sql(data, conn_str):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    insert_query = """
        INSERT INTO WellPermits (Owner, Township, Range, Section, Quarter, Latitude, Longitude, Purpose, Depth, Flow)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(insert_query, (
        data["Owner"], data["Township"], data["Range"], int(data["Section"]) if data["Section"] else None,
        data["Quarter"], data["Latitude"], data["Longitude"], data["Purpose"], 
        int(data["Depth"]) if data["Depth"] else None, int(data["Flow"]) if data["Flow"] else None
    ))
    conn.commit()
    cursor.close()
    conn.close()
    print("Saved to SQL Server!")

# Push it to ArcGIS Online
def import_to_gis_from_sql(conn_str, gis_url, layer_item_id):
    conn = pyodbc.connect(conn_str)
    query = "SELECT * FROM WellPermits WHERE GISImported = 0"
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("Nothing new to import.")
        return

    gis = GIS(gis_url, "your_username", "your_password")
    well_layer = gis.content.get(layer_item_id).layers[0]

    features = []
    for _, row in df.iterrows():
        feature = {
            "attributes": {col: row[col] for col in df.columns if col not in ["Latitude", "Longitude"]},
            "geometry": {"x": row["Longitude"], "y": row["Latitude"], "spatialReference": {"wkid": 4326}}
        }
        features.append(feature)

    result = well_layer.edit_features(adds=features)
    print("ArcGIS Import Result:", result)

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("UPDATE WellPermits SET GISImported = 1 WHERE PermitID IN ({})".format(
        ",".join(str(row["PermitID"]) for _, row in df.iterrows())))
    conn.commit()
    conn.close()

# Run it
if __name__ == "__main__":
    site_url = "https://yourdomain.sharepoint.com/sites/IDWR"
    username = "your_email@domain.com"
    password = "your_password"
    library_name = "Well Permits"
    file_name = "WellPermit_Example.pdf"

    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=your_server_name;"
        "DATABASE=IDWR_GIS;"
        "UID=your_sql_username;"
        "PWD=your_sql_password"
    )

    gis_url = "https://www.arcgis.com"
    layer_item_id = "your_layer_item_id"

    pdf_path = get_pdf_from_sharepoint(site_url, username, password, library_name, file_name)
    form_data = extract_form_data(pdf_path)
    store_in_sql(form_data, conn_str)
    import_to_gis_from_sql(conn_str, gis_url, layer_item_id)

How to Use It
Toss your well permit PDF into your SharePoint library.

Update the script with your details (URLs, usernames, etc.).

Run it: python well_importer.py.

Check your SQL Server table and ArcGIS Online layer—boom, it’s there!

Tips
If the PDF format changes, tweak the regex patterns in extract_form_data. They’re picky about exact matches.

SharePoint passwords in plain text are sketchy—look into OAuth if you’re feeling fancy.

Test with a dummy PDF first. I messed up the lat/long conversion a couple times before I got it right.

What Could Go Wrong
SharePoint might barf if the file isn’t found—double-check file_name.

SQL Server might choke on bad data (e.g., missing numbers). Add some error checks if you’re paranoid.

ArcGIS Online needs edit perms on the layer, or it’ll just sit there complaining.

Future Ideas
Loop through all PDFs in the SharePoint folder instead of one at a time.

Hook it up to Power Automate to run when a new PDF drops.

Add a log file so you know what’s up.

