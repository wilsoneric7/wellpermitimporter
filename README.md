Well Permit GIS Importer
This script pulls well permit PDFs from SharePoint, grabs the important info (like owner name and coordinates), saves it to SQL Server, and pushes it to ArcGIS Online as map points. It’s meant to cut out the copy/paste grind—especially if you’re dealing with a bunch of IDWR permits.

What It Does
Pulls a PDF from SharePoint

Extracts info like owner, lat/long, township, range, and purpose

Inserts that into a SQL Server table

Adds the data as points on an ArcGIS Online layer

Requirements
Python 3.7+ (tested on 3.9)

Python libraries:
pdfplumber, pandas, pyodbc, office365-rest-python-client, arcgis

Access to:

A SharePoint site with permit PDFs

A SQL Server DB (table script is included)

An ArcGIS Online feature layer (editable)

Setup
1. Install dependencies
bash
Copy
Edit
pip install pdfplumber pandas pyodbc office365-rest-python-client arcgis
2. Create the SQL table
Run this in your database:

sql
Copy
Edit
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
3. Configure your script
Edit well_importer.py with your actual SharePoint URL, login info, DB connection string, and ArcGIS layer details.

Running It
Put the script in a folder (e.g. ~/WellImporter)

Upload a test PDF to SharePoint

Run the script:

bash
Copy
Edit
python well_importer.py
Check your SQL table and ArcGIS map

Folder Contents
well_importer.py – main script

README.md – this file

create_table.sql – sets up the SQL table

requirements.txt – optional, just lists the pip packages

sample.pdf – optional dummy permit for testing

.gitignore – ignore cache and temp files

A Few Notes
The PDF parsing uses regex—it’s picky. Adjust if your form layout changes

Hardcoded passwords aren’t ideal, but they work. OAuth is better if you’ve got time

Start with a test PDF until you know it’s working

You’ll need edit rights on your ArcGIS layer

If nothing imports, check the GISImported flag in SQL

Nice-to-Haves (Future Ideas)
Loop through all PDFs, not just one

Tie it into Power Automate for scheduled runs

Add basic logging

Feel free to improve or fork it
