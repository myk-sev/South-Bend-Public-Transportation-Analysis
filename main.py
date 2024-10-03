import requests
import pandas as pd
import time

PROGRESS_FILE_NAME = "temp_transit_duration.csv"
RIDES_FILE_NAME = "EPP_Uber_Rides_2024.csv"
API_KEY_FILE_NAME = "api-key.txt"
HOME_TO_SCHOOL = {"Start": (41.525,-87.507), "End": (41.555,-87.335), "Request Time": int(time.time())}
EPP_EXAMPLE = {"Start": (41.691,-86.181), "End": (41.704,-86.236), "Request Time": int(time.time())}
API_CALL_RATE = 25 #per second

#TO DO:
# Have API call rate check on time pass rather than waiting a set time.
# Have script check for existence of bad coordinates file. If it is there create a new file.
# add a time out function for requests
# add the functionality to determine what requests still need to be made/have been made


def encode_endpoints (start_coords: tuple, end_coords: tuple) -> str :
    """Formats coordinates for inclusion in request url."""
    origin = f"origin={start_coords[0]},{start_coords[1]}"
    destination = f"destination={end_coords[0]},{end_coords[1]}"

    return f"{origin}&{destination}"


def construct_request(coordinates: dict, api_key: str) -> str:
    """Creates the request used to retrieve route recommendations from Google."""
    output_format = "json"
    endpoints = encode_endpoints(coordinates["Start"], coordinates["End"])
    mode = "mode=transit"
    departure_time = "departure_time=" + str(coordinates["Request Time"])

    request_url = f"https://maps.googleapis.com/maps/api/directions/"
    request_url += f"{output_format}?{endpoints}&key={api_key}&{mode}&{departure_time}"

    return request_url


def retrieve_rides(filename: str) -> list:
    """Retrieve all start & end coordinates from EPP data file."""
    rides_df = pd.read_csv(filename)
    ride_coords = []
    for i in range(rides_df.shape[0]):
        start_lat = rides_df.iloc[i]["Pickup Latitude"]
        start_long = rides_df.iloc[i]["Pickup Longitude"]
        end_lat = rides_df.iloc[i]["Drop Off Latitude"]
        end_long = rides_df.iloc[i]["Drop Off Longitude"]
        id = rides_df.iloc[i]["ID"]

        request_date = rides_df.iloc[i]["Request Date"]
        request_time = rides_df.iloc[i]["Request Time"]
        epoch_time = calculate_epoch_time(request_date, request_time)
        

        route_coords = {"Start": (start_lat, start_long), "End": (end_lat,end_long), "ID": id, "Request Time": epoch_time}
        ride_coords.append(route_coords)

    return ride_coords


def pool_data(rides: list):
    """Pool data into dictionary format to construct final dataframe."""
    ids = []
    start_lats = []
    start_longs = []
    end_lats = []
    end_longs = []
    durations = []
    for ride in rides:
        if "Transit Duration" in ride:
            ids.append(ride["ID"])
            start_lats.append(ride["Start"][0])
            start_longs.append(ride["Start"][1])
            end_lats.append(ride["End"][0])
            end_longs.append(ride["End"][1])
            durations.append(ride["Transit Duration"])

    df_input = {"ID": ids,
                "Pickup Latitude": start_lats,
                "Pickup Longitude": start_longs,
                "Drop Off Latitude": end_lats,
                "Drop Off Longitude": end_longs,
                "Transit Duration": durations}

    duration_df = pd.DataFrame(df_input)

    return duration_df


def add_transit_duration(rides, api_key):
    """Retrieves quickest public transportation directions from Google API. Duration is added to rides dictionary."""
    for ride in rides:
        request_url = construct_request(ride, api_key)
        transit_route = requests.get(request_url)

        time.sleep(1/API_CALL_RATE)

        if ride["Start"] == ride["End"]:
            with open("bad coordinates.txt", "a+") as file:
                file.write("Bad coordinates at ID:" + str(ride["ID"]) + '\n')
                file.write(request_url + '\n')

            print("Bad coordinates at ID:", ride["ID"])
            print(request_url)
            continue

        json = transit_route.json()
        try:
            if check_transit_mode(json): #ensures no driving directions were given
                ride["Transit Duration"] = json["routes"][0]["legs"][0]["duration"]["text"]
                print(str(ride["ID"]) + ":", ride["Transit Duration"])

                with open(PROGRESS_FILE_NAME, "a+") as file:
                    temp_data = str(ride["ID"]) + ","
                    temp_data += ride["Transit Duration"] + "\n"
                    file.write(temp_data)

            else:
                print("Route:", ride["ID"], "was provided driving directions.")
                print(request_url)

        except:
            print("No route at ID:", ride["ID"])
            # print(request_url)
            with open("bad coordinates.txt", "a+") as file:
                file.write("No route at ID:" + str(ride["ID"]) + '\n')
                file.write(request_url + '\n')


    return rides


def test():
    api_key = retrieve_api_key(API_KEY_FILE_NAME)
    #request_url = construct_request(HOME_TO_SCHOOL, api_key)
    request_url = construct_request(EPP_EXAMPLE, api_key)
    print(request_url)
    route = requests.get(request_url)
    duration = route.json()["routes"][0]["legs"][0]["duration"]["text"]
    print(duration)


def check_transit_mode(json):
    """Checks the direction type given by api call."""
    for step in json["routes"][0]["legs"][0]["steps"]:
        if step["travel_mode"] == "DRIVING":
            return False
    return True


def calculate_epoch_time(date_str, time_str)->int:
    """Determines seconds since start of epoch based on local time entry."""
    # convert date info into struct_time object
    split_date = date_str.split('/')
    for i in range(len(split_date)):
        if len(split_date[i]) == 1:
            split_date[i] = '0' + split_date[i] #formatting requires double-digit entries for days & months
    fixed_date = '/'.join(split_date)
    date_format = "%m/%d/%Y"
    date_struct = time.strptime(fixed_date, date_format)  # documentation https://docs.python.org/3.12/library/datetime.html#strftime-and-strptime-behavior

    # convert time info into struct_time object
    if len(time_str) == 7:
        time_str = '0' + time_str #double-digit formatting is also required for minutes and hours
    time_format = "%I:%M %p"
    time_struct = time.strptime(time_str, time_format)

    #combined into a single struct_time object
    input_tuple = (date_struct.tm_year, #year
                   date_struct.tm_mon, #month
                   date_struct.tm_mday, #day
                   time_struct.tm_hour, #hour
                   time_struct.tm_min, #minute
                   time_struct.tm_sec, #second
                   date_struct.tm_wday, #day of week
                   date_struct.tm_yday, #day of year
                   date_struct.tm_isdst) #daylight savings flag

    combined_struct = time.struct_time(input_tuple)

    #convert struct_time object into # of seconds since 1970
    epoch_time = time.mktime(combined_struct)
    return int(epoch_time) #google api requires whole numbers


def create_error_record():
    pass


def retrieve_api_key(file_name: str) -> str:
    """Retrieves the contents of the specified file."""
    api_key = ""
    with open(file_name, "r") as file:
        api_key = file.read()
    return api_key


if __name__ == "__main__":
    test()
    # api_key = retrieve_api_key(API_KEY_FILE_NAME)
    # # request_url = construct_request(EPP_EXAMPLE)
    # # route = requests.get(request_url)
    # # print(request_url)
    # # json = route.json()
    #
    # all_rides = retrieve_rides(RIDES_FILE_NAME)
    # all_rides = add_transit_duration(all_rides, api_key)
    # #
    # transit_duration_df = pool_data(all_rides)
    # transit_start_df = transit_duration_df[["ID", "Pickup Latitude", "Pickup Longitude", "Transit Duration"]]
    # transit_end_df = transit_duration_df[["ID", "Drop Off Latitude", "Drop Off Longitude", "Transit Duration"]]
    # transit_start_df.to_csv("Transit_Duration_Start_Coords v1.csv")
    # transit_end_df.to_csv("Transit_Duration_End_Coords v1.csv")
