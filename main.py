import pdfplumber
import pandas as pd
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
import re

# Extracts key fields from a well permit PDF
def extract_form_data(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()

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

        data = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            data[key] = match.group(1) if match else None

        # Convert DMS coordinates to decimal
        def dms_to_dd(dms_str):
            if not dms_str:
                return None
            d, m, s = re.findall(r"(\d+)", dms_str)
            dd = float(d) + float(m)/60 + float(s)/3600
            return dd if dms_str[-1] in ["N", "E"] else -dd

        data["Latitude_DD"] = dms_to_dd(data["Latitude"])
        data["Longitude_DD"] = dms_to_dd(data["Longitude"])

        return data

# Preps data for ArcGIS
def prepare_gis_data(data):
    df = pd.DataFrame([data])
    df = df[[
        "Owner_Name", "Township", "Range", "Section", "Quarter",
        "Latitude_DD", "Longitude_DD", "Purpose", "Depth_ft", "Flow_gpm"
    ]]
    df.columns = [
        "Owner", "Township", "Range", "Section", "Quarter",
        "Latitude", "Longitude", "Purpose", "Depth", "Flow"
    ]
    return df

# Pushes the data to an ArcGIS Online feature layer
def import_to_gis(df, gis_url, item_id):
    gis = GIS(gis_url, "your_username", "your_password")  # Replace with your login
    layer = gis.content.get(item_id).layers[0]

    features = []
    for _, row in df.iterrows():
        features.append({
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
                "spatialReference": {"wkid": 4326}
            }
        })

    result = layer.edit_features(adds=features)
    print("Import result:", result)

# --- Main ---
if __name__ == "__main__":
    pdf_path = "path_to_your_form.pdf"  # Replace with your file path
    form_data = extract_form_data(pdf_path)
    print("Extracted:", form_data)

    gis_data = prepare_gis_data(form_data)
    print("Prepared for GIS:\n", gis_data)

    gis_url = "https://www.arcgis.com"
    layer_item_id = "your_layer_item_id"  # Replace this too
    import_to_gis(gis_data, gis_url, layer_item_id)

