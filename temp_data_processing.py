import pandas as pd

TEMP_INPUT_NAME = "temp_transit_duration"
RIDES_FILE_NAME = "EPP_Uber_Rides_2024"


def fix_time(time: str) -> int:
    total_time = 0
    components = time.split(" ")
    for i in range(0,len(components),2):
        pair = components[i:i+2]
        if "day" in pair[1]:
            total_time += 60 * 24 * int(pair[0])
        elif "hour" in pair[1]:
            total_time += 60 * int(pair[0])
        elif "min" in pair[1]:
            total_time += int(pair[0])
        else:
            raise "invalid time type. investigate"

    return total_time


if __name__ == "__main__":
    tempDF = pd.read_csv(TEMP_INPUT_NAME + ".csv")
    eppDF = pd.read_csv(RIDES_FILE_NAME + ".csv")

    start_data = {"ID": [], "Latitude": [], "Longitude": [], "Public Transit Duration": []}
    end_data = {"ID": [], "Latitude": [], "Longitude": [], "Public Transit Duration": []}

    start_data["ID"] = tempDF["ID"]
    end_data["ID"] = tempDF["ID"]
    for i, google_row in tempDF.iterrows():
        id = google_row["ID"]
        epp_row = eppDF.iloc[id]

        start_data["Latitude"].append(epp_row["Pickup Latitude"])
        start_data["Longitude"].append(epp_row["Pickup Longitude"])
        start_data["Public Transit Duration"].append(fix_time(google_row["Time"]))

        end_data["Latitude"].append(epp_row["Drop Off Latitude"])
        end_data["Longitude"].append(epp_row["Drop Off Longitude"])
        end_data["Public Transit Duration"].append(fix_time(google_row["Time"]))


    start_coords_df = pd.DataFrame(start_data)
    end_coords_df = pd.DataFrame(end_data)

    start_coords_df.to_csv(TEMP_INPUT_NAME + "_start_coords.csv")
    end_coords_df.to_csv(TEMP_INPUT_NAME + "_end_coords.csv")