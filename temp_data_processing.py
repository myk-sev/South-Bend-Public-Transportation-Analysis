import pandas as pd

TEMP_INPUT_NAME = "temp_transit_duration"
RIDES_FILE_NAME = "EPP_Uber_Rides_2024"


def fix_time(time: str) -> int:
    converted_time = 0

    if "mins" in time: time = time.removesuffix(" mins")
    else: time = time.removesuffix(" min")

    if len(time) < 3:
        converted_time += int(time)
    else:
        converted_time += 60 * int(time[0])
        time = time[1:]

        if "hours" in time: time = time.removeprefix(" hours ")
        else: time = time.removeprefix(" hour ")

        converted_time += int(time)

    return converted_time


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





