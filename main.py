import pdfplumber
import pandas as pd
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
import re

# Step 1: Extract Data from the Form (PDF)
def extract_form_data(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]  # Assume single-page form
        text = page.extract_text()

        # Define regex patterns for key fields
        patterns = {
            "Owner_Name": r"Well Owner Name: (.+)",
            "Township": r"Township: (\d+[NS])",
            "Range": r"Range: (\d+[EW])",
            "Section": r"Section: (\d+)",
            "Quarter": r"Quarter-Quarter: (.+)",
            "Latitude": r"Latitude: (\d+° \d+' \d+\" [NS])",
            "Longitude": r"Longitude: (\d+° \d+' \d+\" [EW])",
            "Purpose": r"Purpose of Use: \[X\] (\w+)",
            "Depth_ft": r"Proposed Depth: (\d+) feet",
            "Flow_gpm": r"Estimated Flow Rate: (\d+) gpm"
        }

        # Extract data using regex
        extracted_data = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            extracted_data[key] = match.group(1) if match else None

        # Convert lat/long to decimal degrees
        def dms_to_dd(dms_str):
            if not dms_str:
                return None
            d, m, s = re.findall(r"(\d+)", dms_str)
            direction = dms_str[-1]  # N/S or E/W
            dd = float(d) + float(m)/60 + float(s)/3600
            return dd if direction in ["N", "E"] else -dd

        extracted_data["Latitude_DD"] = dms_to_dd(extracted_data["Latitude"])
        extracted_data["Longitude_DD"] = dms_to_dd(extracted_data["Longitude"])

        return extracted_data

# Step 2: Structure Data for GIS
def prepare_gis_data(extracted_data):
    # Create a DataFrame
    df = pd.DataFrame([extracted_data])
    # Select relevant columns
    gis_df = df[["Owner_Name", "Township", "Range", "Section", "Quarter", 
                 "Latitude_DD", "Longitude_DD", "Purpose", "Depth_ft", "Flow_gpm"]]
    # Rename for GIS compatibility
    gis_df.columns = ["Owner", "Township", "Range", "Section", "Quarter", 
                      "Latitude", "Longitude", "Purpose", "Depth", "Flow"]
    return gis_df

# Step 3: Import into ArcGIS Online
def import_to_gis(gis_df, gis_url, layer_name):
    # Connect to ArcGIS Online
    gis = GIS("https://www.arcgis.com", "your_username", "your_password")  # Replace with credentials

    # Access the target feature layer
    well_layer = gis.content.get(layer_name).layers[0]  # e.g., "IDWR_Wells" item ID

    # Convert DataFrame to feature set
    features = []
    for index, row in gis_df.iterrows():
        feature = {
            "attributes": {
                "Owner": row["Owner"],
                "Township": row["Township"],
                "Range": row["Range"],
                "Section": row["Section"],
                "Quarter": row["Quarter"],
                "Purpose": row["Purpose"],
                "Depth": row["Depth"],
                "Flow": row["Flow"]
            },
            "geometry": {
                "x": row["Longitude"],
                "y": row["Latitude"],
                "spatialReference": {"wkid": 4326}  # WGS84
            }
        }
        features.append(feature)

    # Add features to the layer
    result = well_layer.edit_features(adds=features)
    print("Import result:", result)

# Main Workflow
if __name__ == "__main__":
    # Path to your PDF form
    pdf_path = "path_to_your_form.pdf"  # Replace with actual path

    # Extract data
    form_data = extract_form_data(pdf_path)
    print("Extracted Data:", form_data)

    # Prepare for GIS
    gis_data = prepare_gis_data(form_data)
    print("GIS-Ready Data:\n", gis_data)

    # Import into ArcGIS Online
    gis_url = "https://www.arcgis.com"
    layer_item_id = "your_layer_item_id"  # Replace with your feature layer's Item ID
    import_to_gis(gis_data, gis_url, layer_item_id)
