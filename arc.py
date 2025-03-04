import arcpy
arcpy.env.workspace = "path_to_gdb"
arcpy.management.CreateFeatureclass("Wells.gdb", "New_Wells", "POINT")
with arcpy.da.InsertCursor("New_Wells", ["SHAPE@XY", "Owner", "Purpose"]) as cursor:
    cursor.insertRow([(form_data["Longitude_DD"], form_data["Latitude_DD"]), 
                      form_data["Owner_Name"], form_data["Purpose"]])
