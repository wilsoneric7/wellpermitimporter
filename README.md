Well Permit GIS Importer
Hey! This is a Python script I hacked together to pull well permit PDFs from SharePoint, yank out the important bits (like owner and coordinates), stash them in SQL Server, and then plop them into ArcGIS Online as map points. It’s great for cutting out manual GIS grunt work, like if you’re dealing with IDWR well permits. I’m no wizard, but it gets the job done—hope it works for you too!
What It Does
Grabs a well permit PDF from SharePoint.

Digs out details like owner name, Township/Range, lat/long, and well purpose.

Drops the data into a SQL Server table.

Pulls that data and adds it as points to an ArcGIS Online layer.

What You’ll Need
Python 3: I used 3.9, but 3.7+ should work.

Libraries: See the “Dependencies” section below.

SharePoint: A site with a library (e.g., “Well Permits”) where PDFs are uploaded.

SQL Server: A database with a WellPermits table (script included below).

ArcGIS Online: An account with a feature layer you can edit.

Credentials: For SharePoint, SQL Server, and ArcGIS Online.

Setup
1. Get Python Ready
Check if you’ve got Python:
Windows: Open Command Prompt (Win + R, type cmd), run python --version.

Mac/Linux: Open Terminal, run python3 --version.

See something like Python 3.9.5? You’re set. If not, grab it from python.org/downloads.

Windows tip: Check “Add Python to PATH” during install.

No Python? Install it, then test again.

2. Grab the Dependencies
Open your terminal and run:

pip install pdfplumber pandas pyodbc office365-rest-python-client arcgis

If pip flops, try python -m pip install ... or pip3 install ... (Mac/Linux).

What they do:
pdfplumber: Reads PDFs.

pandas: Handles data tables.

pyodbc: Talks to SQL Server.

office365-rest-python-client: Hits up SharePoint.

arcgis: Connects to ArcGIS Online.

3. Set Up SQL Server
Open SQL Server Management Studio (or your tool) and run this to make the table:
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

This holds your well data. Tweak it if your DB’s picky.

4. Save the Script
Copy the code below into a file called well_importer.py.

Stick it in a folder like C:\Users\YourName\WellImporter (Windows) or ~/Documents/WellImporter (Mac/Linux).

5. Tweak the Config
Open well_importer.py in Notepad, VS Code, or whatever.

Update these with your stuff:
SharePoint: site_url, username, password, library_name, file_name.

SQL Server: conn_str (server name, DB, etc.).

ArcGIS: gis_url, layer_item_id, your_username, your_password.

Example: If your SharePoint is https://company.sharepoint.com/sites/IDWR, swap that in.

6. Test PDF
Drop a sample well permit PDF (e.g., WellPermit_Example.pdf) into your SharePoint library.

Set file_name in the script to match.

The Code (well_importer.py)
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

Where to Run It on Your Computer
Folder: Pick a spot like C:\Users\YourName\WellImporter (Windows) or ~/Documents/WellImporter (Mac/Linux). Save well_importer.py there. Keeps it tidy.

Terminal:
Windows: Open Command Prompt (Win + R, cmd), cd C:\Users\YourName\WellImporter.

Mac/Linux: Open Terminal, cd ~/Documents/WellImporter.

Run It:
Windows: python well_importer.py

Mac/Linux: python3 well_importer.py

If Python’s not found, reinstall with “Add to PATH” checked (Windows) or use brew install python (Mac), sudo apt install python3 (Linux).

How to Use It
Upload your well permit PDF to your SharePoint library.

Update the script with your SharePoint, SQL, and ArcGIS details.

Open terminal, cd to your folder, and run the script.

Check SQL Server (WellPermits table) and ArcGIS Online (your layer) to see the magic.

Stuff in This Repo
well_importer.py: The main script.

README.md: This file you’re reading.

create_table.sql: The SQL script for the WellPermits table (below).

(Optional) sample.pdf: A fake well permit PDF if I had one handy—make your own for testing.

create_table.sql
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

Tips
Regex in extract_form_data is fussy—if your PDF’s different, tweak those patterns.

SharePoint passwords in the script? Kinda sketchy. Look into OAuth if you’ve got time.

Test with a dummy PDF first—I botched the lat/long math a couple times.

What Could Go Wrong
SharePoint: File not found? Check file_name.

SQL: Bad data (e.g., missing numbers) might crash it—add error checks if you’re worried.

ArcGIS: No edit perms on the layer? It’ll whine.

Future Ideas
Loop through all PDFs in SharePoint instead of one.

Hook it to Power Automate for auto-runs.

Add a log file to track what’s happening.

Fork it, tweak it, yell at me if it breaks. Happy coding!
What to Include in the GitHub Repo
Here’s what I’d toss into the repo so anyone (including you) can grab it and go:
well_importer.py:
The script above. Main deal.

README.md:
The text above, saved as README.md. GitHub loves this—it’s your landing page.

create_table.sql:
A separate file with the SQL table script. Makes it easy to set up the DB.

Optional: requirements.txt:
A file listing dependencies for pip. Add this:

pdfplumber
pandas
pyodbc
office365-rest-python-client
arcgis

Then folks can just run pip install -r requirements.txt.

Optional: Sample PDF:
If you’ve got a dummy well permit PDF, throw it in as sample.pdf. I’d make one matching the regex (e.g., “Well Owner Name: John Doe”, etc.), but you’d need to whip that up since I can’t here.

Optional: .gitignore:
Add this to keep junk out of the repo:

__pycache__/
*.pyc
*.pyo
*.pdf  # Unless you include a sample

Folder Structure

WellImporter/
│
├── well_importer.py
├── README.md
├── create_table.sql
├── requirements.txt  (optional)
├── sample.pdf        (optional, if you make one)
└── .gitignore        (optional)



